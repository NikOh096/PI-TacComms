# Pinned Xiph RNNoise source and upstream hash-verified model.
if(NOT RNN_SOURCE)
    set(RNN_SOURCE "${CMAKE_CURRENT_LIST_DIR}/inspect/rnnoise-70f1d256acd4b34a572f999a05c87bf00b67730d")
endif()
set(RNN_NAMES denoise rnn pitch kiss_fft celt_lpc nnet nnet_default parse_lpcnet_weights rnnoise_data rnnoise_tables)
set(RNN_FILES "")
foreach(name IN LISTS RNN_NAMES)
    list(APPEND RNN_FILES "${RNN_SOURCE}/src/${name}.c")
endforeach()
add_library(taccomms-rnnoise STATIC ${RNN_FILES})
target_include_directories(taccomms-rnnoise PUBLIC "${RNN_SOURCE}/include" PRIVATE "${RNN_SOURCE}/src")
target_compile_definitions(taccomms-rnnoise PRIVATE RNNOISE_BUILD)
set_target_properties(taccomms-rnnoise PROPERTIES POSITION_INDEPENDENT_CODE ON)
if(MSVC)
    target_compile_options(taccomms-rnnoise PRIVATE /O2)
    target_compile_definitions(taccomms-rnnoise PRIVATE restrict=__restrict)
else()
    target_compile_options(taccomms-rnnoise PRIVATE -O3)
    # Generated weights intentionally initialize float arrays with decimal
    # literals. Mumble's global conversion warnings otherwise produce enormous
    # diagnostics for this data-only source on GCC.
    set_source_files_properties("${RNN_SOURCE}/src/rnnoise_data.c" PROPERTIES
        COMPILE_OPTIONS "-Wno-conversion;-Wno-sign-conversion;-Wno-float-conversion")
    target_link_libraries(taccomms-rnnoise PUBLIC m)
endif()
