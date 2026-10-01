// TacComms optional server-side Opus speech cleanup.
#pragma once
#include <cstddef>
#include <cstdint>
#include <memory>

class TacCommsDenoiser {
public:
    enum class Action { Bypass, Filtered, Drop };
    struct Result {
        Action action = Action::Bypass;
        int bytes = 0;
        int samples = 0;
        double milliseconds = 0;
        bool neuralFiltered = false;
    };
    TacCommsDenoiser();
    ~TacCommsDenoiser();
    TacCommsDenoiser(const TacCommsDenoiser&) = delete;
    TacCommsDenoiser& operator=(const TacCommsDenoiser&) = delete;
    Result process(const unsigned char *packet, std::size_t bytes,
                   std::uint64_t sequence, bool enabled,
                   unsigned char *output, std::size_t capacity);
    // An instance belongs to exactly one ServerUser. It is destroyed on logout.
private:
    struct Impl;
    std::unique_ptr<Impl> impl;
};

// Root-owned mode file; defaults to bypass if missing or malformed.
bool tacCommsNoiseEnabled();
