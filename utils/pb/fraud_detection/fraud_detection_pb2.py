# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: fraud_detection/fraud_detection.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n%fraud_detection/fraud_detection.proto\x12\x0f\x66raud_detection\"A\n\x0c\x46raudRequest\x12\x10\n\x08order_id\x18\x01 \x01(\t\x12\x0f\n\x07user_id\x18\x02 \x01(\t\x12\x0e\n\x06\x61mount\x18\x03 \x01(\x02\"!\n\rFraudResponse\x12\x10\n\x08is_fraud\x18\x01 \x01(\x08\x32[\n\x0c\x46raudService\x12K\n\nCheckFraud\x12\x1d.fraud_detection.FraudRequest\x1a\x1e.fraud_detection.FraudResponseb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'fraud_detection.fraud_detection_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _FRAUDREQUEST._serialized_start=58
  _FRAUDREQUEST._serialized_end=123
  _FRAUDRESPONSE._serialized_start=125
  _FRAUDRESPONSE._serialized_end=158
  _FRAUDSERVICE._serialized_start=160
  _FRAUDSERVICE._serialized_end=251
# @@protoc_insertion_point(module_scope)
