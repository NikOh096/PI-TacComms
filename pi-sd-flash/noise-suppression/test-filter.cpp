#include "TacCommsDenoiser.h"
#include <opus.h>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <thread>
#include <vector>

using Clock=std::chrono::steady_clock;
void check(bool result,const char *message) {if(!result)throw std::runtime_error(message);}
struct Codec {
    OpusEncoder *encoder;
    OpusDecoder *decoder;
    Codec() {
        int error=0;
        encoder=opus_encoder_create(48000,1,OPUS_APPLICATION_VOIP,&error);
        check(encoder && !error,"input encoder");
        opus_encoder_ctl(encoder,OPUS_SET_BITRATE(24000));
        opus_encoder_ctl(encoder,OPUS_SET_VBR(0));
        decoder=opus_decoder_create(48000,1,&error);
        check(decoder && !error,"output decoder");
    }
    ~Codec(){opus_encoder_destroy(encoder);opus_decoder_destroy(decoder);}
};

int main(int argc,char **argv) {
    try {
        if(argc==2 && std::string(argv[1])=="--load") {
            constexpr int users=4,frames=1000;
            std::array<Codec,users> codecs;
            std::array<TacCommsDenoiser,users> filters;
            std::array<float,960> pcm{};
            std::array<unsigned char,1275> encoded{},output{};
            double total=0,maximum=0;unsigned fallback=0;
            auto next=Clock::now();
            for(int frame=0;frame<frames;++frame) {
                for(int user=0;user<users;++user) {
                    for(int i=0;i<960;++i) {
                        double t=(frame*960+i)/48000.0,frequency=135+user*37;
                        pcm[i]=float(.06*std::sin(6.2831853*frequency*t)+.025*std::sin(6.2831853*frequency*3*t)+.02*std::sin(6.2831853*2441*t));
                    }
                    int n=opus_encode_float(codecs[user].encoder,pcm.data(),960,encoded.data(),1275);
                    check(n>0,"load encode");
                    auto r=filters[user].process(encoded.data(),n,frame*2,true,output.data(),output.size());
                    check(r.action==TacCommsDenoiser::Action::Filtered,"load dropped or bypassed audio");
                    total+=r.milliseconds;maximum=std::max(maximum,r.milliseconds);
                    if(!r.neuralFiltered)++fallback;
                }
                next+=std::chrono::milliseconds(20);std::this_thread::sleep_until(next);
            }
            check(fallback==0,"neural fallback during sustained load");
            check(total/(frames*users)<4,"insufficient processing headroom for four active speakers");
            std::cout<<"{\"passed\":true,\"active_speakers\":4,\"seconds\":20,\"mean_processing_ms_per_20ms_packet\":"
                     <<total/(frames*users)<<",\"max_processing_ms\":"<<maximum<<",\"neural_fallback_frames\":"<<fallback<<"}\n";
            return 0;
        }
        if(argc==4 && (std::string(argv[1])=="--pcm" || std::string(argv[1])=="--baseline")) {
            const bool enabled=std::string(argv[1])=="--pcm";
            FILE *in=std::fopen(argv[2],"rb"),*out=std::fopen(argv[3],"wb");
            check(in && out,"PCM files");
            Codec codec;TacCommsDenoiser filter;
            std::array<short,960> pcm{};std::array<short,2880> decoded{};
            std::array<unsigned char,1275> encoded{},filtered{};
            unsigned frame=0,fallback=0;double totalMs=0;auto next=Clock::now();
            while(std::fread(pcm.data(),sizeof(short),pcm.size(),in)==pcm.size()) {
                int n=opus_encode(codec.encoder,pcm.data(),960,encoded.data(),1275);
                check(n>0,"PCM encode");
                auto r=filter.process(encoded.data(),n,frame*2,enabled,filtered.data(),filtered.size());
                check(r.action==(enabled?TacCommsDenoiser::Action::Filtered:TacCommsDenoiser::Action::Bypass),"PCM filter action");
                check(opus_decode(codec.decoder,enabled?filtered.data():encoded.data(),enabled?r.bytes:n,decoded.data(),2880,0)==960,"PCM decode");
                check(std::fwrite(decoded.data(),sizeof(short),960,out)==960,"PCM output write");
                totalMs+=r.milliseconds;++frame;
                if(enabled && !r.neuralFiltered)++fallback;
                next+=std::chrono::milliseconds(20);std::this_thread::sleep_until(next);
            }
            std::fclose(in);std::fclose(out);
            std::cout<<"{\"frames\":"<<frame<<",\"mean_processing_ms\":"<<totalMs/frame
                     <<",\"neural_fallback_frames\":"<<fallback<<"}\n";
            return 0;
        }
        constexpr int Users=4,Frames=250;
        std::array<Codec,Users> codecs;
        std::array<TacCommsDenoiser,Users> filters;
        std::array<float,960> pcm{};
        std::array<float,2880> decoded{};
        std::array<unsigned char,1275> encoded{},output{};
        std::mt19937 random(42);
        std::uniform_real_distribution<float> noise(-0.08f,0.08f);
        double inputEnergy=0,outputEnergy=0,totalMs=0,maxMs=0,silentPeak=0;
        unsigned fallback=0;
        auto next=Clock::now();
        for(int frame=0;frame<Frames;++frame) {
            for(int user=0;user<Users;++user) {
                for(auto &x:pcm)x=user==0?noise(random):0.0f;
                int n=opus_encode_float(codecs[user].encoder,pcm.data(),960,encoded.data(),1275);
                check(n>0,"encode noise/silence");
                auto r=filters[user].process(encoded.data(),n,frame*2,true,output.data(),output.size());
                check(r.action==TacCommsDenoiser::Action::Filtered,"unexpected active-stream bypass");
                check(r.samples==960,"frame duration changed");
                check(opus_decode_float(codecs[user].decoder,output.data(),r.bytes,decoded.data(),2880,0)==960,"output decode");
                totalMs+=r.milliseconds;maxMs=std::max(maxMs,r.milliseconds);
                if(!r.neuralFiltered)++fallback;
                if(user==0 && frame>50)for(int i=0;i<960;++i) {
                    inputEnergy+=pcm[i]*pcm[i];outputEnergy+=decoded[i]*decoded[i];
                }
                if(user!=0)for(int i=0;i<960;++i) silentPeak=std::max(silentPeak,std::abs(double(decoded[i])));
                if(frame==40 && user==0) {
                    auto duplicate=filters[user].process(encoded.data(),n,frame*2,true,output.data(),output.size());
                    check(duplicate.action==TacCommsDenoiser::Action::Drop,"duplicate not rejected");
                }
            }
            next+=std::chrono::milliseconds(20);std::this_thread::sleep_until(next);
        }
        const double reduction=10*std::log10(inputEnergy/std::max(outputEnergy,1e-20));
        std::cerr<<"Noise reduction: "<<reduction<<" dB; mean processing "<<totalMs/(Frames*Users)
                 <<" ms; max "<<maxMs<<" ms; silent peak "<<silentPeak<<'\n';
        check(reduction>6,"noise attenuation under 6 dB");
        check(silentPeak<1e-4,"audio leaked between users");
        check(fallback==0,"neural model fell back under test load");
        auto bypass=filters[0].process(encoded.data(),60,1000,false,output.data(),output.size());
        check(bypass.action==TacCommsDenoiser::Action::Bypass,"off mode must bypass");
        auto marker=filters[0].process(nullptr,0,1000,true,output.data(),output.size());
        check(marker.action==TacCommsDenoiser::Action::Bypass,"empty end marker lost");
        Codec codec;
        for(int samples:{480,960,1920,2880}) {
            TacCommsDenoiser fresh;std::array<float,2880> silence{};
            int n=opus_encode_float(codec.encoder,silence.data(),samples,encoded.data(),1275);
            check(n>0,"duration encode");
            auto r=fresh.process(encoded.data(),n,0,true,output.data(),output.size());
            check(r.action==TacCommsDenoiser::Action::Filtered && r.samples==samples,"duration support");
        }
        // A real 120 ms packet must bypass without decoding into a 60 ms buffer.
        OpusRepacketizer *rp=opus_repacketizer_create();
        opus_encoder_ctl(codec.encoder,OPUS_SET_EXPERT_FRAME_DURATION(OPUS_FRAMESIZE_20_MS));
        std::array<float,960> silence{};
        std::array<std::array<unsigned char,1275>,6> parts{};
        for(int i=0;i<6;++i) {
            int n=opus_encode_float(codec.encoder,silence.data(),960,parts[i].data(),1275);
            check(n>0,"120 ms part encode");
            check(opus_repacketizer_cat(rp,parts[i].data(),n)==OPUS_OK,"120 ms repacketize");
        }
        int n=opus_repacketizer_out(rp,encoded.data(),1275);
        check(n>0 && opus_packet_get_nb_samples(encoded.data(),n,48000)==5760,"120 ms packet");
        TacCommsDenoiser fresh;
        check(fresh.process(encoded.data(),n,0,true,output.data(),output.size()).action==TacCommsDenoiser::Action::Bypass,"120 ms must bypass");
        opus_repacketizer_destroy(rp);
        // Malformed framing must not enter the decoder; disabled mode stays exact bypass.
        std::array<unsigned char,2> invalid{{0xff,0xff}};
        check(fresh.process(invalid.data(),invalid.size(),0,true,output.data(),output.size()).action==TacCommsDenoiser::Action::Drop,"invalid duration accepted");
        check(fresh.process(invalid.data(),invalid.size(),0,false,output.data(),output.size()).action==TacCommsDenoiser::Action::Bypass,"disabled path changed");
        // Exercise repeated codec/model destruction and initialization on mode changes.
        for(int i=0;i<100;++i) {
            TacCommsDenoiser resetTest;
            n=opus_encode_float(codec.encoder,silence.data(),960,encoded.data(),1275);
            check(n>0,"reset encode");
            for(int pass=0;pass<3;++pass) {
                auto r=resetTest.process(encoded.data(),n,0,true,output.data(),output.size());
                check(r.action==TacCommsDenoiser::Action::Filtered,"reset state failed");
                resetTest.process(encoded.data(),n,0,false,output.data(),output.size());
            }
        }
        std::cout<<"{\"passed\":true,\"simultaneous_users\":"<<Users
                 <<",\"noise_reduction_db\":"<<reduction
                 <<",\"mean_processing_ms_per_20ms_packet\":"<<totalMs/(Frames*Users)
                 <<",\"max_processing_ms\":"<<maxMs<<",\"silent_user_peak\":"<<silentPeak<<"}\n";
    }catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}
}
