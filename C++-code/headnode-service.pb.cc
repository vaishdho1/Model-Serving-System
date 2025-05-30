// Generated by the protocol buffer compiler.  DO NOT EDIT!
// NO CHECKED-IN PROTOBUF GENCODE
// source: headnode-service.proto
// Protobuf C++ Version: 5.29.3

#include "headnode-service.pb.h"

#include <algorithm>
#include <type_traits>
#include "google/protobuf/io/coded_stream.h"
#include "google/protobuf/generated_message_tctable_impl.h"
#include "google/protobuf/extension_set.h"
#include "google/protobuf/generated_message_util.h"
#include "google/protobuf/wire_format_lite.h"
#include "google/protobuf/descriptor.h"
#include "google/protobuf/generated_message_reflection.h"
#include "google/protobuf/reflection_ops.h"
#include "google/protobuf/wire_format.h"
// @@protoc_insertion_point(includes)

// Must be included last.
#include "google/protobuf/port_def.inc"
PROTOBUF_PRAGMA_INIT_SEG
namespace _pb = ::google::protobuf;
namespace _pbi = ::google::protobuf::internal;
namespace _fl = ::google::protobuf::internal::field_layout;
namespace raylet {

inline constexpr HeadNodeRequest::Impl_::Impl_(
    ::_pbi::ConstantInitialized) noexcept
      : final_result_(
            &::google::protobuf::internal::fixed_address_empty_string,
            ::_pbi::ConstantInitialized()),
        original_task_id_(
            &::google::protobuf::internal::fixed_address_empty_string,
            ::_pbi::ConstantInitialized()),
        _cached_size_{0} {}

template <typename>
PROTOBUF_CONSTEXPR HeadNodeRequest::HeadNodeRequest(::_pbi::ConstantInitialized)
#if defined(PROTOBUF_CUSTOM_VTABLE)
    : ::google::protobuf::Message(_class_data_.base()),
#else   // PROTOBUF_CUSTOM_VTABLE
    : ::google::protobuf::Message(),
#endif  // PROTOBUF_CUSTOM_VTABLE
      _impl_(::_pbi::ConstantInitialized()) {
}
struct HeadNodeRequestDefaultTypeInternal {
  PROTOBUF_CONSTEXPR HeadNodeRequestDefaultTypeInternal() : _instance(::_pbi::ConstantInitialized{}) {}
  ~HeadNodeRequestDefaultTypeInternal() {}
  union {
    HeadNodeRequest _instance;
  };
};

PROTOBUF_ATTRIBUTE_NO_DESTROY PROTOBUF_CONSTINIT
    PROTOBUF_ATTRIBUTE_INIT_PRIORITY1 HeadNodeRequestDefaultTypeInternal _HeadNodeRequest_default_instance_;

inline constexpr HeadNodeReply::Impl_::Impl_(
    ::_pbi::ConstantInitialized) noexcept
      : message_(
            &::google::protobuf::internal::fixed_address_empty_string,
            ::_pbi::ConstantInitialized()),
        ack_{false},
        _cached_size_{0} {}

template <typename>
PROTOBUF_CONSTEXPR HeadNodeReply::HeadNodeReply(::_pbi::ConstantInitialized)
#if defined(PROTOBUF_CUSTOM_VTABLE)
    : ::google::protobuf::Message(_class_data_.base()),
#else   // PROTOBUF_CUSTOM_VTABLE
    : ::google::protobuf::Message(),
#endif  // PROTOBUF_CUSTOM_VTABLE
      _impl_(::_pbi::ConstantInitialized()) {
}
struct HeadNodeReplyDefaultTypeInternal {
  PROTOBUF_CONSTEXPR HeadNodeReplyDefaultTypeInternal() : _instance(::_pbi::ConstantInitialized{}) {}
  ~HeadNodeReplyDefaultTypeInternal() {}
  union {
    HeadNodeReply _instance;
  };
};

PROTOBUF_ATTRIBUTE_NO_DESTROY PROTOBUF_CONSTINIT
    PROTOBUF_ATTRIBUTE_INIT_PRIORITY1 HeadNodeReplyDefaultTypeInternal _HeadNodeReply_default_instance_;
}  // namespace raylet
static constexpr const ::_pb::EnumDescriptor**
    file_level_enum_descriptors_headnode_2dservice_2eproto = nullptr;
static constexpr const ::_pb::ServiceDescriptor**
    file_level_service_descriptors_headnode_2dservice_2eproto = nullptr;
const ::uint32_t
    TableStruct_headnode_2dservice_2eproto::offsets[] ABSL_ATTRIBUTE_SECTION_VARIABLE(
        protodesc_cold) = {
        ~0u,  // no _has_bits_
        PROTOBUF_FIELD_OFFSET(::raylet::HeadNodeRequest, _internal_metadata_),
        ~0u,  // no _extensions_
        ~0u,  // no _oneof_case_
        ~0u,  // no _weak_field_map_
        ~0u,  // no _inlined_string_donated_
        ~0u,  // no _split_
        ~0u,  // no sizeof(Split)
        PROTOBUF_FIELD_OFFSET(::raylet::HeadNodeRequest, _impl_.final_result_),
        PROTOBUF_FIELD_OFFSET(::raylet::HeadNodeRequest, _impl_.original_task_id_),
        ~0u,  // no _has_bits_
        PROTOBUF_FIELD_OFFSET(::raylet::HeadNodeReply, _internal_metadata_),
        ~0u,  // no _extensions_
        ~0u,  // no _oneof_case_
        ~0u,  // no _weak_field_map_
        ~0u,  // no _inlined_string_donated_
        ~0u,  // no _split_
        ~0u,  // no sizeof(Split)
        PROTOBUF_FIELD_OFFSET(::raylet::HeadNodeReply, _impl_.ack_),
        PROTOBUF_FIELD_OFFSET(::raylet::HeadNodeReply, _impl_.message_),
};

static const ::_pbi::MigrationSchema
    schemas[] ABSL_ATTRIBUTE_SECTION_VARIABLE(protodesc_cold) = {
        {0, -1, -1, sizeof(::raylet::HeadNodeRequest)},
        {10, -1, -1, sizeof(::raylet::HeadNodeReply)},
};
static const ::_pb::Message* const file_default_instances[] = {
    &::raylet::_HeadNodeRequest_default_instance_._instance,
    &::raylet::_HeadNodeReply_default_instance_._instance,
};
const char descriptor_table_protodef_headnode_2dservice_2eproto[] ABSL_ATTRIBUTE_SECTION_VARIABLE(
    protodesc_cold) = {
    "\n\026headnode-service.proto\022\006raylet\"A\n\017Head"
    "NodeRequest\022\024\n\014final_result\030\001 \001(\t\022\030\n\020ori"
    "ginal_task_id\030\002 \001(\t\"-\n\rHeadNodeReply\022\013\n\003"
    "ack\030\001 \001(\010\022\017\n\007message\030\002 \001(\t2Q\n\017HeadNodeSe"
    "rvice\022>\n\014ReportResult\022\027.raylet.HeadNodeR"
    "equest\032\025.raylet.HeadNodeReplyb\006proto3"
};
static ::absl::once_flag descriptor_table_headnode_2dservice_2eproto_once;
PROTOBUF_CONSTINIT const ::_pbi::DescriptorTable descriptor_table_headnode_2dservice_2eproto = {
    false,
    false,
    237,
    descriptor_table_protodef_headnode_2dservice_2eproto,
    "headnode-service.proto",
    &descriptor_table_headnode_2dservice_2eproto_once,
    nullptr,
    0,
    2,
    schemas,
    file_default_instances,
    TableStruct_headnode_2dservice_2eproto::offsets,
    file_level_enum_descriptors_headnode_2dservice_2eproto,
    file_level_service_descriptors_headnode_2dservice_2eproto,
};
namespace raylet {
// ===================================================================

class HeadNodeRequest::_Internal {
 public:
};

HeadNodeRequest::HeadNodeRequest(::google::protobuf::Arena* arena)
#if defined(PROTOBUF_CUSTOM_VTABLE)
    : ::google::protobuf::Message(arena, _class_data_.base()) {
#else   // PROTOBUF_CUSTOM_VTABLE
    : ::google::protobuf::Message(arena) {
#endif  // PROTOBUF_CUSTOM_VTABLE
  SharedCtor(arena);
  // @@protoc_insertion_point(arena_constructor:raylet.HeadNodeRequest)
}
inline PROTOBUF_NDEBUG_INLINE HeadNodeRequest::Impl_::Impl_(
    ::google::protobuf::internal::InternalVisibility visibility, ::google::protobuf::Arena* arena,
    const Impl_& from, const ::raylet::HeadNodeRequest& from_msg)
      : final_result_(arena, from.final_result_),
        original_task_id_(arena, from.original_task_id_),
        _cached_size_{0} {}

HeadNodeRequest::HeadNodeRequest(
    ::google::protobuf::Arena* arena,
    const HeadNodeRequest& from)
#if defined(PROTOBUF_CUSTOM_VTABLE)
    : ::google::protobuf::Message(arena, _class_data_.base()) {
#else   // PROTOBUF_CUSTOM_VTABLE
    : ::google::protobuf::Message(arena) {
#endif  // PROTOBUF_CUSTOM_VTABLE
  HeadNodeRequest* const _this = this;
  (void)_this;
  _internal_metadata_.MergeFrom<::google::protobuf::UnknownFieldSet>(
      from._internal_metadata_);
  new (&_impl_) Impl_(internal_visibility(), arena, from._impl_, from);

  // @@protoc_insertion_point(copy_constructor:raylet.HeadNodeRequest)
}
inline PROTOBUF_NDEBUG_INLINE HeadNodeRequest::Impl_::Impl_(
    ::google::protobuf::internal::InternalVisibility visibility,
    ::google::protobuf::Arena* arena)
      : final_result_(arena),
        original_task_id_(arena),
        _cached_size_{0} {}

inline void HeadNodeRequest::SharedCtor(::_pb::Arena* arena) {
  new (&_impl_) Impl_(internal_visibility(), arena);
}
HeadNodeRequest::~HeadNodeRequest() {
  // @@protoc_insertion_point(destructor:raylet.HeadNodeRequest)
  SharedDtor(*this);
}
inline void HeadNodeRequest::SharedDtor(MessageLite& self) {
  HeadNodeRequest& this_ = static_cast<HeadNodeRequest&>(self);
  this_._internal_metadata_.Delete<::google::protobuf::UnknownFieldSet>();
  ABSL_DCHECK(this_.GetArena() == nullptr);
  this_._impl_.final_result_.Destroy();
  this_._impl_.original_task_id_.Destroy();
  this_._impl_.~Impl_();
}

inline void* HeadNodeRequest::PlacementNew_(const void*, void* mem,
                                        ::google::protobuf::Arena* arena) {
  return ::new (mem) HeadNodeRequest(arena);
}
constexpr auto HeadNodeRequest::InternalNewImpl_() {
  return ::google::protobuf::internal::MessageCreator::CopyInit(sizeof(HeadNodeRequest),
                                            alignof(HeadNodeRequest));
}
PROTOBUF_CONSTINIT
PROTOBUF_ATTRIBUTE_INIT_PRIORITY1
const ::google::protobuf::internal::ClassDataFull HeadNodeRequest::_class_data_ = {
    ::google::protobuf::internal::ClassData{
        &_HeadNodeRequest_default_instance_._instance,
        &_table_.header,
        nullptr,  // OnDemandRegisterArenaDtor
        nullptr,  // IsInitialized
        &HeadNodeRequest::MergeImpl,
        ::google::protobuf::Message::GetNewImpl<HeadNodeRequest>(),
#if defined(PROTOBUF_CUSTOM_VTABLE)
        &HeadNodeRequest::SharedDtor,
        ::google::protobuf::Message::GetClearImpl<HeadNodeRequest>(), &HeadNodeRequest::ByteSizeLong,
            &HeadNodeRequest::_InternalSerialize,
#endif  // PROTOBUF_CUSTOM_VTABLE
        PROTOBUF_FIELD_OFFSET(HeadNodeRequest, _impl_._cached_size_),
        false,
    },
    &HeadNodeRequest::kDescriptorMethods,
    &descriptor_table_headnode_2dservice_2eproto,
    nullptr,  // tracker
};
const ::google::protobuf::internal::ClassData* HeadNodeRequest::GetClassData() const {
  ::google::protobuf::internal::PrefetchToLocalCache(&_class_data_);
  ::google::protobuf::internal::PrefetchToLocalCache(_class_data_.tc_table);
  return _class_data_.base();
}
PROTOBUF_CONSTINIT PROTOBUF_ATTRIBUTE_INIT_PRIORITY1
const ::_pbi::TcParseTable<1, 2, 0, 59, 2> HeadNodeRequest::_table_ = {
  {
    0,  // no _has_bits_
    0, // no _extensions_
    2, 8,  // max_field_number, fast_idx_mask
    offsetof(decltype(_table_), field_lookup_table),
    4294967292,  // skipmap
    offsetof(decltype(_table_), field_entries),
    2,  // num_field_entries
    0,  // num_aux_entries
    offsetof(decltype(_table_), field_names),  // no aux_entries
    _class_data_.base(),
    nullptr,  // post_loop_handler
    ::_pbi::TcParser::GenericFallback,  // fallback
    #ifdef PROTOBUF_PREFETCH_PARSE_TABLE
    ::_pbi::TcParser::GetTable<::raylet::HeadNodeRequest>(),  // to_prefetch
    #endif  // PROTOBUF_PREFETCH_PARSE_TABLE
  }, {{
    // string original_task_id = 2;
    {::_pbi::TcParser::FastUS1,
     {18, 63, 0, PROTOBUF_FIELD_OFFSET(HeadNodeRequest, _impl_.original_task_id_)}},
    // string final_result = 1;
    {::_pbi::TcParser::FastUS1,
     {10, 63, 0, PROTOBUF_FIELD_OFFSET(HeadNodeRequest, _impl_.final_result_)}},
  }}, {{
    65535, 65535
  }}, {{
    // string final_result = 1;
    {PROTOBUF_FIELD_OFFSET(HeadNodeRequest, _impl_.final_result_), 0, 0,
    (0 | ::_fl::kFcSingular | ::_fl::kUtf8String | ::_fl::kRepAString)},
    // string original_task_id = 2;
    {PROTOBUF_FIELD_OFFSET(HeadNodeRequest, _impl_.original_task_id_), 0, 0,
    (0 | ::_fl::kFcSingular | ::_fl::kUtf8String | ::_fl::kRepAString)},
  }},
  // no aux_entries
  {{
    "\26\14\20\0\0\0\0\0"
    "raylet.HeadNodeRequest"
    "final_result"
    "original_task_id"
  }},
};

PROTOBUF_NOINLINE void HeadNodeRequest::Clear() {
// @@protoc_insertion_point(message_clear_start:raylet.HeadNodeRequest)
  ::google::protobuf::internal::TSanWrite(&_impl_);
  ::uint32_t cached_has_bits = 0;
  // Prevent compiler warnings about cached_has_bits being unused
  (void) cached_has_bits;

  _impl_.final_result_.ClearToEmpty();
  _impl_.original_task_id_.ClearToEmpty();
  _internal_metadata_.Clear<::google::protobuf::UnknownFieldSet>();
}

#if defined(PROTOBUF_CUSTOM_VTABLE)
        ::uint8_t* HeadNodeRequest::_InternalSerialize(
            const MessageLite& base, ::uint8_t* target,
            ::google::protobuf::io::EpsCopyOutputStream* stream) {
          const HeadNodeRequest& this_ = static_cast<const HeadNodeRequest&>(base);
#else   // PROTOBUF_CUSTOM_VTABLE
        ::uint8_t* HeadNodeRequest::_InternalSerialize(
            ::uint8_t* target,
            ::google::protobuf::io::EpsCopyOutputStream* stream) const {
          const HeadNodeRequest& this_ = *this;
#endif  // PROTOBUF_CUSTOM_VTABLE
          // @@protoc_insertion_point(serialize_to_array_start:raylet.HeadNodeRequest)
          ::uint32_t cached_has_bits = 0;
          (void)cached_has_bits;

          // string final_result = 1;
          if (!this_._internal_final_result().empty()) {
            const std::string& _s = this_._internal_final_result();
            ::google::protobuf::internal::WireFormatLite::VerifyUtf8String(
                _s.data(), static_cast<int>(_s.length()), ::google::protobuf::internal::WireFormatLite::SERIALIZE, "raylet.HeadNodeRequest.final_result");
            target = stream->WriteStringMaybeAliased(1, _s, target);
          }

          // string original_task_id = 2;
          if (!this_._internal_original_task_id().empty()) {
            const std::string& _s = this_._internal_original_task_id();
            ::google::protobuf::internal::WireFormatLite::VerifyUtf8String(
                _s.data(), static_cast<int>(_s.length()), ::google::protobuf::internal::WireFormatLite::SERIALIZE, "raylet.HeadNodeRequest.original_task_id");
            target = stream->WriteStringMaybeAliased(2, _s, target);
          }

          if (PROTOBUF_PREDICT_FALSE(this_._internal_metadata_.have_unknown_fields())) {
            target =
                ::_pbi::WireFormat::InternalSerializeUnknownFieldsToArray(
                    this_._internal_metadata_.unknown_fields<::google::protobuf::UnknownFieldSet>(::google::protobuf::UnknownFieldSet::default_instance), target, stream);
          }
          // @@protoc_insertion_point(serialize_to_array_end:raylet.HeadNodeRequest)
          return target;
        }

#if defined(PROTOBUF_CUSTOM_VTABLE)
        ::size_t HeadNodeRequest::ByteSizeLong(const MessageLite& base) {
          const HeadNodeRequest& this_ = static_cast<const HeadNodeRequest&>(base);
#else   // PROTOBUF_CUSTOM_VTABLE
        ::size_t HeadNodeRequest::ByteSizeLong() const {
          const HeadNodeRequest& this_ = *this;
#endif  // PROTOBUF_CUSTOM_VTABLE
          // @@protoc_insertion_point(message_byte_size_start:raylet.HeadNodeRequest)
          ::size_t total_size = 0;

          ::uint32_t cached_has_bits = 0;
          // Prevent compiler warnings about cached_has_bits being unused
          (void)cached_has_bits;

          ::_pbi::Prefetch5LinesFrom7Lines(&this_);
           {
            // string final_result = 1;
            if (!this_._internal_final_result().empty()) {
              total_size += 1 + ::google::protobuf::internal::WireFormatLite::StringSize(
                                              this_._internal_final_result());
            }
            // string original_task_id = 2;
            if (!this_._internal_original_task_id().empty()) {
              total_size += 1 + ::google::protobuf::internal::WireFormatLite::StringSize(
                                              this_._internal_original_task_id());
            }
          }
          return this_.MaybeComputeUnknownFieldsSize(total_size,
                                                     &this_._impl_._cached_size_);
        }

void HeadNodeRequest::MergeImpl(::google::protobuf::MessageLite& to_msg, const ::google::protobuf::MessageLite& from_msg) {
  auto* const _this = static_cast<HeadNodeRequest*>(&to_msg);
  auto& from = static_cast<const HeadNodeRequest&>(from_msg);
  // @@protoc_insertion_point(class_specific_merge_from_start:raylet.HeadNodeRequest)
  ABSL_DCHECK_NE(&from, _this);
  ::uint32_t cached_has_bits = 0;
  (void) cached_has_bits;

  if (!from._internal_final_result().empty()) {
    _this->_internal_set_final_result(from._internal_final_result());
  }
  if (!from._internal_original_task_id().empty()) {
    _this->_internal_set_original_task_id(from._internal_original_task_id());
  }
  _this->_internal_metadata_.MergeFrom<::google::protobuf::UnknownFieldSet>(from._internal_metadata_);
}

void HeadNodeRequest::CopyFrom(const HeadNodeRequest& from) {
// @@protoc_insertion_point(class_specific_copy_from_start:raylet.HeadNodeRequest)
  if (&from == this) return;
  Clear();
  MergeFrom(from);
}


void HeadNodeRequest::InternalSwap(HeadNodeRequest* PROTOBUF_RESTRICT other) {
  using std::swap;
  auto* arena = GetArena();
  ABSL_DCHECK_EQ(arena, other->GetArena());
  _internal_metadata_.InternalSwap(&other->_internal_metadata_);
  ::_pbi::ArenaStringPtr::InternalSwap(&_impl_.final_result_, &other->_impl_.final_result_, arena);
  ::_pbi::ArenaStringPtr::InternalSwap(&_impl_.original_task_id_, &other->_impl_.original_task_id_, arena);
}

::google::protobuf::Metadata HeadNodeRequest::GetMetadata() const {
  return ::google::protobuf::Message::GetMetadataImpl(GetClassData()->full());
}
// ===================================================================

class HeadNodeReply::_Internal {
 public:
};

HeadNodeReply::HeadNodeReply(::google::protobuf::Arena* arena)
#if defined(PROTOBUF_CUSTOM_VTABLE)
    : ::google::protobuf::Message(arena, _class_data_.base()) {
#else   // PROTOBUF_CUSTOM_VTABLE
    : ::google::protobuf::Message(arena) {
#endif  // PROTOBUF_CUSTOM_VTABLE
  SharedCtor(arena);
  // @@protoc_insertion_point(arena_constructor:raylet.HeadNodeReply)
}
inline PROTOBUF_NDEBUG_INLINE HeadNodeReply::Impl_::Impl_(
    ::google::protobuf::internal::InternalVisibility visibility, ::google::protobuf::Arena* arena,
    const Impl_& from, const ::raylet::HeadNodeReply& from_msg)
      : message_(arena, from.message_),
        _cached_size_{0} {}

HeadNodeReply::HeadNodeReply(
    ::google::protobuf::Arena* arena,
    const HeadNodeReply& from)
#if defined(PROTOBUF_CUSTOM_VTABLE)
    : ::google::protobuf::Message(arena, _class_data_.base()) {
#else   // PROTOBUF_CUSTOM_VTABLE
    : ::google::protobuf::Message(arena) {
#endif  // PROTOBUF_CUSTOM_VTABLE
  HeadNodeReply* const _this = this;
  (void)_this;
  _internal_metadata_.MergeFrom<::google::protobuf::UnknownFieldSet>(
      from._internal_metadata_);
  new (&_impl_) Impl_(internal_visibility(), arena, from._impl_, from);
  _impl_.ack_ = from._impl_.ack_;

  // @@protoc_insertion_point(copy_constructor:raylet.HeadNodeReply)
}
inline PROTOBUF_NDEBUG_INLINE HeadNodeReply::Impl_::Impl_(
    ::google::protobuf::internal::InternalVisibility visibility,
    ::google::protobuf::Arena* arena)
      : message_(arena),
        _cached_size_{0} {}

inline void HeadNodeReply::SharedCtor(::_pb::Arena* arena) {
  new (&_impl_) Impl_(internal_visibility(), arena);
  _impl_.ack_ = {};
}
HeadNodeReply::~HeadNodeReply() {
  // @@protoc_insertion_point(destructor:raylet.HeadNodeReply)
  SharedDtor(*this);
}
inline void HeadNodeReply::SharedDtor(MessageLite& self) {
  HeadNodeReply& this_ = static_cast<HeadNodeReply&>(self);
  this_._internal_metadata_.Delete<::google::protobuf::UnknownFieldSet>();
  ABSL_DCHECK(this_.GetArena() == nullptr);
  this_._impl_.message_.Destroy();
  this_._impl_.~Impl_();
}

inline void* HeadNodeReply::PlacementNew_(const void*, void* mem,
                                        ::google::protobuf::Arena* arena) {
  return ::new (mem) HeadNodeReply(arena);
}
constexpr auto HeadNodeReply::InternalNewImpl_() {
  return ::google::protobuf::internal::MessageCreator::CopyInit(sizeof(HeadNodeReply),
                                            alignof(HeadNodeReply));
}
PROTOBUF_CONSTINIT
PROTOBUF_ATTRIBUTE_INIT_PRIORITY1
const ::google::protobuf::internal::ClassDataFull HeadNodeReply::_class_data_ = {
    ::google::protobuf::internal::ClassData{
        &_HeadNodeReply_default_instance_._instance,
        &_table_.header,
        nullptr,  // OnDemandRegisterArenaDtor
        nullptr,  // IsInitialized
        &HeadNodeReply::MergeImpl,
        ::google::protobuf::Message::GetNewImpl<HeadNodeReply>(),
#if defined(PROTOBUF_CUSTOM_VTABLE)
        &HeadNodeReply::SharedDtor,
        ::google::protobuf::Message::GetClearImpl<HeadNodeReply>(), &HeadNodeReply::ByteSizeLong,
            &HeadNodeReply::_InternalSerialize,
#endif  // PROTOBUF_CUSTOM_VTABLE
        PROTOBUF_FIELD_OFFSET(HeadNodeReply, _impl_._cached_size_),
        false,
    },
    &HeadNodeReply::kDescriptorMethods,
    &descriptor_table_headnode_2dservice_2eproto,
    nullptr,  // tracker
};
const ::google::protobuf::internal::ClassData* HeadNodeReply::GetClassData() const {
  ::google::protobuf::internal::PrefetchToLocalCache(&_class_data_);
  ::google::protobuf::internal::PrefetchToLocalCache(_class_data_.tc_table);
  return _class_data_.base();
}
PROTOBUF_CONSTINIT PROTOBUF_ATTRIBUTE_INIT_PRIORITY1
const ::_pbi::TcParseTable<1, 2, 0, 36, 2> HeadNodeReply::_table_ = {
  {
    0,  // no _has_bits_
    0, // no _extensions_
    2, 8,  // max_field_number, fast_idx_mask
    offsetof(decltype(_table_), field_lookup_table),
    4294967292,  // skipmap
    offsetof(decltype(_table_), field_entries),
    2,  // num_field_entries
    0,  // num_aux_entries
    offsetof(decltype(_table_), field_names),  // no aux_entries
    _class_data_.base(),
    nullptr,  // post_loop_handler
    ::_pbi::TcParser::GenericFallback,  // fallback
    #ifdef PROTOBUF_PREFETCH_PARSE_TABLE
    ::_pbi::TcParser::GetTable<::raylet::HeadNodeReply>(),  // to_prefetch
    #endif  // PROTOBUF_PREFETCH_PARSE_TABLE
  }, {{
    // string message = 2;
    {::_pbi::TcParser::FastUS1,
     {18, 63, 0, PROTOBUF_FIELD_OFFSET(HeadNodeReply, _impl_.message_)}},
    // bool ack = 1;
    {::_pbi::TcParser::SingularVarintNoZag1<bool, offsetof(HeadNodeReply, _impl_.ack_), 63>(),
     {8, 63, 0, PROTOBUF_FIELD_OFFSET(HeadNodeReply, _impl_.ack_)}},
  }}, {{
    65535, 65535
  }}, {{
    // bool ack = 1;
    {PROTOBUF_FIELD_OFFSET(HeadNodeReply, _impl_.ack_), 0, 0,
    (0 | ::_fl::kFcSingular | ::_fl::kBool)},
    // string message = 2;
    {PROTOBUF_FIELD_OFFSET(HeadNodeReply, _impl_.message_), 0, 0,
    (0 | ::_fl::kFcSingular | ::_fl::kUtf8String | ::_fl::kRepAString)},
  }},
  // no aux_entries
  {{
    "\24\0\7\0\0\0\0\0"
    "raylet.HeadNodeReply"
    "message"
  }},
};

PROTOBUF_NOINLINE void HeadNodeReply::Clear() {
// @@protoc_insertion_point(message_clear_start:raylet.HeadNodeReply)
  ::google::protobuf::internal::TSanWrite(&_impl_);
  ::uint32_t cached_has_bits = 0;
  // Prevent compiler warnings about cached_has_bits being unused
  (void) cached_has_bits;

  _impl_.message_.ClearToEmpty();
  _impl_.ack_ = false;
  _internal_metadata_.Clear<::google::protobuf::UnknownFieldSet>();
}

#if defined(PROTOBUF_CUSTOM_VTABLE)
        ::uint8_t* HeadNodeReply::_InternalSerialize(
            const MessageLite& base, ::uint8_t* target,
            ::google::protobuf::io::EpsCopyOutputStream* stream) {
          const HeadNodeReply& this_ = static_cast<const HeadNodeReply&>(base);
#else   // PROTOBUF_CUSTOM_VTABLE
        ::uint8_t* HeadNodeReply::_InternalSerialize(
            ::uint8_t* target,
            ::google::protobuf::io::EpsCopyOutputStream* stream) const {
          const HeadNodeReply& this_ = *this;
#endif  // PROTOBUF_CUSTOM_VTABLE
          // @@protoc_insertion_point(serialize_to_array_start:raylet.HeadNodeReply)
          ::uint32_t cached_has_bits = 0;
          (void)cached_has_bits;

          // bool ack = 1;
          if (this_._internal_ack() != 0) {
            target = stream->EnsureSpace(target);
            target = ::_pbi::WireFormatLite::WriteBoolToArray(
                1, this_._internal_ack(), target);
          }

          // string message = 2;
          if (!this_._internal_message().empty()) {
            const std::string& _s = this_._internal_message();
            ::google::protobuf::internal::WireFormatLite::VerifyUtf8String(
                _s.data(), static_cast<int>(_s.length()), ::google::protobuf::internal::WireFormatLite::SERIALIZE, "raylet.HeadNodeReply.message");
            target = stream->WriteStringMaybeAliased(2, _s, target);
          }

          if (PROTOBUF_PREDICT_FALSE(this_._internal_metadata_.have_unknown_fields())) {
            target =
                ::_pbi::WireFormat::InternalSerializeUnknownFieldsToArray(
                    this_._internal_metadata_.unknown_fields<::google::protobuf::UnknownFieldSet>(::google::protobuf::UnknownFieldSet::default_instance), target, stream);
          }
          // @@protoc_insertion_point(serialize_to_array_end:raylet.HeadNodeReply)
          return target;
        }

#if defined(PROTOBUF_CUSTOM_VTABLE)
        ::size_t HeadNodeReply::ByteSizeLong(const MessageLite& base) {
          const HeadNodeReply& this_ = static_cast<const HeadNodeReply&>(base);
#else   // PROTOBUF_CUSTOM_VTABLE
        ::size_t HeadNodeReply::ByteSizeLong() const {
          const HeadNodeReply& this_ = *this;
#endif  // PROTOBUF_CUSTOM_VTABLE
          // @@protoc_insertion_point(message_byte_size_start:raylet.HeadNodeReply)
          ::size_t total_size = 0;

          ::uint32_t cached_has_bits = 0;
          // Prevent compiler warnings about cached_has_bits being unused
          (void)cached_has_bits;

          ::_pbi::Prefetch5LinesFrom7Lines(&this_);
           {
            // string message = 2;
            if (!this_._internal_message().empty()) {
              total_size += 1 + ::google::protobuf::internal::WireFormatLite::StringSize(
                                              this_._internal_message());
            }
            // bool ack = 1;
            if (this_._internal_ack() != 0) {
              total_size += 2;
            }
          }
          return this_.MaybeComputeUnknownFieldsSize(total_size,
                                                     &this_._impl_._cached_size_);
        }

void HeadNodeReply::MergeImpl(::google::protobuf::MessageLite& to_msg, const ::google::protobuf::MessageLite& from_msg) {
  auto* const _this = static_cast<HeadNodeReply*>(&to_msg);
  auto& from = static_cast<const HeadNodeReply&>(from_msg);
  // @@protoc_insertion_point(class_specific_merge_from_start:raylet.HeadNodeReply)
  ABSL_DCHECK_NE(&from, _this);
  ::uint32_t cached_has_bits = 0;
  (void) cached_has_bits;

  if (!from._internal_message().empty()) {
    _this->_internal_set_message(from._internal_message());
  }
  if (from._internal_ack() != 0) {
    _this->_impl_.ack_ = from._impl_.ack_;
  }
  _this->_internal_metadata_.MergeFrom<::google::protobuf::UnknownFieldSet>(from._internal_metadata_);
}

void HeadNodeReply::CopyFrom(const HeadNodeReply& from) {
// @@protoc_insertion_point(class_specific_copy_from_start:raylet.HeadNodeReply)
  if (&from == this) return;
  Clear();
  MergeFrom(from);
}


void HeadNodeReply::InternalSwap(HeadNodeReply* PROTOBUF_RESTRICT other) {
  using std::swap;
  auto* arena = GetArena();
  ABSL_DCHECK_EQ(arena, other->GetArena());
  _internal_metadata_.InternalSwap(&other->_internal_metadata_);
  ::_pbi::ArenaStringPtr::InternalSwap(&_impl_.message_, &other->_impl_.message_, arena);
        swap(_impl_.ack_, other->_impl_.ack_);
}

::google::protobuf::Metadata HeadNodeReply::GetMetadata() const {
  return ::google::protobuf::Message::GetMetadataImpl(GetClassData()->full());
}
// @@protoc_insertion_point(namespace_scope)
}  // namespace raylet
namespace google {
namespace protobuf {
}  // namespace protobuf
}  // namespace google
// @@protoc_insertion_point(global_scope)
PROTOBUF_ATTRIBUTE_INIT_PRIORITY2 static ::std::false_type
    _static_init2_ PROTOBUF_UNUSED =
        (::_pbi::AddDescriptors(&descriptor_table_headnode_2dservice_2eproto),
         ::std::false_type{});
#include "google/protobuf/port_undef.inc"
