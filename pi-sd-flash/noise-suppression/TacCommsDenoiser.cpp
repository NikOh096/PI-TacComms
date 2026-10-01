#include "TacCommsDenoiser.h"
#include <opus.h>
#ifdef TACCOMMS_MODERN_RNNOISE
#include <rnnoise.h>
using ReNameNoiseDenoiseState = DenoiseState;
#define renamenoise_create rnnoise_create
#define renamenoise_destroy rnnoise_destroy
#define renamenoise_get_frame_size rnnoise_get_frame_size
#define renamenoise_process_frame rnnoise_process_frame
#else
#include <renamenoise.h>
#endif
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <mutex>
#include <string>

namespace {
using Clock = std::chrono::steady_clock;
constexpr int Rate = 48000;
constexpr int Block = 480;
constexpr int MaxSamples = 2880;
constexpr int MaxPacket = 1275;
}

struct TacCommsDenoiser::Impl {
    std::mutex mutex;
    OpusDecoder *decoder = nullptr;
    OpusEncoder *encoder = nullptr;
    ReNameNoiseDenoiseState *noise = nullptr;
    bool running = false;
    bool haveSequence = false;
    std::uint64_t nextSequence = 0;
    Clock::time_point lastPacket = Clock::now();
    Clock::time_point budgetTime = Clock::now();
    // Bound decode/filter work even for tiny compressed packets claiming long audio.
    double sampleBudget = Rate / 5.0;
    Clock::time_point bypassUntil{};
    unsigned overruns = 0;
    std::array<float, MaxSamples> pcm{};
    float limiterGain = 1.0f;

    ~Impl() {
        if (decoder) opus_decoder_destroy(decoder);
        if (encoder) opus_encoder_destroy(encoder);
        if (noise) renamenoise_destroy(noise);
    }
    void reset() {
        if (decoder) opus_decoder_ctl(decoder, OPUS_RESET_STATE);
        if (encoder) opus_encoder_ctl(encoder, OPUS_RESET_STATE);
        // init() allocates GRU buffers; reinitializing a live state leaks them.
        if (noise) renamenoise_destroy(noise);
        noise = nullptr;
        haveSequence = false;
        running = false;
        limiterGain = 1.0f;
    }
    bool initialize() {
        int error = OPUS_OK;
        if (!decoder) decoder = opus_decoder_create(Rate, 1, &error);
        if (!decoder || error != OPUS_OK) return false;
        if (!encoder) {
            encoder = opus_encoder_create(Rate, 1, OPUS_APPLICATION_VOIP, &error);
            if (!encoder || error != OPUS_OK) return false;
            if (opus_encoder_ctl(encoder, OPUS_SET_BITRATE(24000)) != OPUS_OK
                || opus_encoder_ctl(encoder, OPUS_SET_VBR(0)) != OPUS_OK
                || opus_encoder_ctl(encoder, OPUS_SET_COMPLEXITY(5)) != OPUS_OK
                || opus_encoder_ctl(encoder, OPUS_SET_SIGNAL(OPUS_SIGNAL_VOICE)) != OPUS_OK
                || opus_encoder_ctl(encoder, OPUS_SET_DTX(0)) != OPUS_OK) return false;
        }
        if (!noise) noise = renamenoise_create(nullptr);
        return noise && renamenoise_get_frame_size() == Block;
    }
};

TacCommsDenoiser::TacCommsDenoiser() : impl(new Impl) {}
TacCommsDenoiser::~TacCommsDenoiser() = default;

TacCommsDenoiser::Result TacCommsDenoiser::process(
    const unsigned char *packet, std::size_t bytes, std::uint64_t sequence,
    bool enabled, unsigned char *output, std::size_t capacity) {
    Result result;
    auto &s = *impl;
    std::lock_guard<std::mutex> lock(s.mutex);
    const auto start = Clock::now();
    if (!enabled) {
        if (s.running) s.reset();
        return result;
    }
    // Empty end-of-talk markers must still be forwarded unchanged.
    if (!bytes) return result;
    if (!packet || !output || capacity < MaxPacket || bytes > MaxPacket) {
        if (s.running) s.reset();
        return result;
    }
    const int samples = opus_packet_get_nb_samples(packet, static_cast<opus_int32>(bytes), Rate);
    if (samples <= 0 || samples > Rate * 120 / 1000) {
        result.action = Action::Drop;
        return result;
    }
    result.samples = samples;
    // 2.5/5 ms, aggregated >60 ms and stereo/music streams remain unmodified.
    if ((samples != 480 && samples != 960 && samples != 1920 && samples != 2880)
        || opus_packet_get_nb_channels(packet) != 1) {
        if (s.running) s.reset();
        return result;
    }
    const double elapsed = std::chrono::duration<double>(start - s.budgetTime).count();
    s.budgetTime = start;
    s.sampleBudget = std::min(Rate / 5.0, s.sampleBudget + elapsed * Rate);
    if (s.sampleBudget < samples) {
        // Excessively fast senders cannot turn CPU limiting into an unfiltered path.
        result.action = Action::Drop;
        return result;
    }
    s.sampleBudget -= samples;
    const bool idle = start - s.lastPacket > std::chrono::seconds(1);
    if (s.haveSequence && !idle && sequence < s.nextSequence) {
        // Do not feed reordered/duplicate packets into a stateful speech filter.
        result.action = Action::Drop;
        return result;
    }
    if (idle || (s.haveSequence && sequence != s.nextSequence)) s.reset();
    if (!s.initialize()) {
        s.reset();
        result.action = Action::Drop;
        return result;
    }
    const int decoded = opus_decode_float(s.decoder, packet, static_cast<opus_int32>(bytes),
                                         s.pcm.data(), MaxSamples, 0);
    if (decoded != samples) {
        s.reset();
        result.action = Action::Drop;
        return result;
    }
    for (int i = 0; i < samples; ++i) {
        if (!std::isfinite(s.pcm[i])) {
            s.reset();
            result.action = Action::Drop;
            return result;
        }
        s.pcm[i] = std::max(-32768.0f, std::min(32767.0f, s.pcm[i] * 32768.0f));
    }
    if (start >= s.bypassUntil) {
        for (int offset = 0; offset < samples; offset += Block)
            renamenoise_process_frame(s.noise, s.pcm.data() + offset, s.pcm.data() + offset);
        result.neuralFiltered = true;
    }
    for (int i = 0; i < samples; ++i) {
        if (!std::isfinite(s.pcm[i])) {
            s.reset();
            result.action = Action::Drop;
            return result;
        }
        s.pcm[i] = std::max(-1.0f, std::min(1.0f, s.pcm[i] / 32768.0f));
    }
    // Limit digital peaks before encoding. This is not a calibrated headphone
    // SPL limit: codec reconstruction, client gain and headset volume follow it.
    // No gain boost or whole-packet mute; retain quiet speech between impulses.
    constexpr float ceiling = 0.25f; // -12.04 dBFS before Opus encoding
    constexpr float release = 0.9995834201f; // 50 ms at 48 kHz
    for (int i = 0; i < samples; ++i) {
        const float amplitude = std::abs(s.pcm[i]);
        const float wanted = amplitude > ceiling ? ceiling / amplitude : 1.0f;
        s.limiterGain = wanted < s.limiterGain ? wanted
            : release * s.limiterGain + (1.0f - release) * wanted;
        s.pcm[i] *= s.limiterGain;
    }
    const int encoded = opus_encode_float(s.encoder, s.pcm.data(), samples, output, MaxPacket);
    if (encoded <= 0) {
        s.reset();
        result.action = Action::Drop;
        return result;
    }
    s.running = true;
    s.haveSequence = sequence <= std::numeric_limits<std::uint64_t>::max() - samples / Block;
    s.nextSequence = s.haveSequence ? sequence + samples / Block : 0;
    s.lastPacket = start;
    result.action = Action::Filtered;
    result.bytes = encoded;
    result.milliseconds = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    // Avoid sustained overload. Subsequent packets retain the lightweight limiter
    // while temporarily skipping the neural filter.
    s.overruns = result.milliseconds > samples * 1000.0 / Rate ? s.overruns + 1 : 0;
    // One scheduler pause should not disable speech enhancement for five seconds.
    if (s.overruns >= 3) {
        s.bypassUntil = Clock::now() + std::chrono::seconds(5);
        s.overruns = 0;
    }
    return result;
}

bool tacCommsNoiseEnabled() {
    static std::mutex mutex;
    static auto nextRead = Clock::time_point{};
    static bool enabled = false;
    std::lock_guard<std::mutex> lock(mutex);
    const auto now = Clock::now();
    if (now >= nextRead) {
        const char *overridePath = std::getenv("TACCOMMS_NOISE_CONFIG");
        std::ifstream config(overridePath ? overridePath : "/etc/taccomms-noise.conf");
        std::string mode;
        std::getline(config, mode);
        enabled = mode == "on";
        nextRead = now + std::chrono::seconds(1);
    }
    return enabled;
}
