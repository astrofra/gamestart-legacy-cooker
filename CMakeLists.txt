cmake_minimum_required(VERSION 3.10)

project(gamestart_legacy_cooker_c LANGUAGES C)

set(ZLIB_SOURCES
    third_party/zlib/adler32.c
    third_party/zlib/compress.c
    third_party/zlib/crc32.c
    third_party/zlib/deflate.c
    third_party/zlib/inffast.c
    third_party/zlib/inflate.c
    third_party/zlib/inftrees.c
    third_party/zlib/trees.c
    third_party/zlib/uncompr.c
    third_party/zlib/zutil.c
)

add_library(gamestart_cooker_zlib STATIC ${ZLIB_SOURCES})
target_include_directories(gamestart_cooker_zlib PUBLIC third_party/zlib)

add_executable(gamestart-cooker-c c/gamestart_cooker.c)
target_link_libraries(gamestart-cooker-c PRIVATE gamestart_cooker_zlib)
target_compile_features(gamestart-cooker-c PRIVATE c_std_99)

if(MSVC)
    target_compile_definitions(gamestart-cooker-c PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()

