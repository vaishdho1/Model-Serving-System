cmake_minimum_required(VERSION 3.22)
project(ModelServer CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")

# --- Define Build Options ---
# By default, neither executable is built. The environment must explicitly opt-in.
option(BUILD_HTTP_PROXY "Build the http_proxy executable" OFF)

# --- Common Proto Generation (Needed by both targets) ---
find_package(gRPC REQUIRED)
set(PROTO_SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src/protos)
set(PROTO_GEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src/generated)
file(GLOB PROTO_FILES "${PROTO_SRC_DIR}/*.proto")

set(PROTO_GENERATED_SOURCES "")
foreach(PROTO_FILE ${PROTO_FILES})
    get_filename_component(BASENAME ${PROTO_FILE} NAME_WE)
    list(APPEND PROTO_GENERATED_SOURCES
        "${PROTO_GEN_DIR}/${BASENAME}.pb.cc"
        "${PROTO_GEN_DIR}/${BASENAME}.grpc.pb.cc"
    )
endforeach()

add_custom_command(
    OUTPUT ${PROTO_GENERATED_SOURCES}
    COMMAND ${CMAKE_COMMAND} -E make_directory ${PROTO_GEN_DIR}
    COMMAND ${Protobuf_PROTOC_EXECUTABLE}
        --proto_path=${PROTO_SRC_DIR}
        --cpp_out=${PROTO_GEN_DIR}
        --grpc_out=${PROTO_GEN_DIR}
        --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
        ${PROTO_FILES}
    DEPENDS ${PROTO_FILES}
    COMMENT "Generating Protobuf C++ sources"
)

add_custom_target(generate_protos ALL DEPENDS ${PROTO_GENERATED_SOURCES})


# --- Target: http_proxy (Conditional Build) ---
if(BUILD_HTTP_PROXY)
    message(STATUS "BUILD_HTTP_PROXY is ON. Configuring target.")
    # Find dependencies specific to the http_proxy
    find_package(Boost REQUIRED COMPONENTS program_options thread)
    find_package(prometheus-cpp REQUIRED)
    find_package(Threads REQUIRED)
    find_package(asio-grpc CONFIG REQUIRED)

    add_executable(http_proxy
        src/components/headNode/http_proxy.cpp
        src/lib/deployment_handle.cpp
        ${PROTO_GENERATED_SOURCES}
    )
    add_dependencies(http_proxy generate_protos)

    target_link_libraries(http_proxy PRIVATE
        Threads::Threads
        asio-grpc::asio-grpc
        gRPC::grpc++
        protobuf::libprotobuf
        Boost::program_options
        Boost::thread
        prometheus-cpp::core
        prometheus-cpp::pull
    )
    target_include_directories(http_proxy PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${asio-grpc_INCLUDE_DIRS}
    )
    install(TARGETS http_proxy DESTINATION bin)
endif()


