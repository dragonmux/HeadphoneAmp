from functools import cached_property
from usb_protocol.emitters.descriptor import ConstructEmitter, ComplexDescriptorEmitter
from usb_protocol.emitters.descriptors.standard import InterfaceAssociationDescriptorEmitter
from usb_protocol.emitters.descriptors.uac3 import (
	InputTerminalDescriptorEmitter, OutputTerminalDescriptorEmitter
)
from .descriptors import (
	AudioChannels, ConnectorAttributes, ConnectorColour,
	MonoFeatureUnitDescriptor, StereoFeatureUnitDescriptor
)

__all__ = (
	'HeaderDescriptor',
	'InputTerminalDescriptor',
	'OutputTerminalDescriptor',
	'FeatureUnitDescriptor',
	'ConnectorDescriptor',
	'AudioChannels',
	'ConnectorAttributes',
	'ConnectorColour',
)

class HeaderDescriptorEmitter(ComplexDescriptorEmitter):
	def __init__(self):
		super().__init__(self.DESCRIPTOR_FORMAT)
		self._parent = None
		self._subordinates = []

	@cached_property
	def DESCRIPTOR_FORMAT(self):
		from usb_protocol.emitters.descriptors.uac3 import HeaderDescriptor
		return HeaderDescriptor

	def add_subordinate_descriptor(self, subordinate):
		""" Adds a subordinate descriptor to the relevant parent descriptor.

		Parameter:
			subordinate -- The subordinate descriptor to add; can be an emitter,
							or a bytes-like object.
		"""
		if hasattr(subordinate, 'emit'):
			subordinate = subordinate.emit()
		else:
			subordinate = bytes(subordinate)

		self._parent.add_subordinate_descriptor(subordinate)

	def _pre_emit(self):
		subordinate_length = sum(len(sub) for sub in self._subordinates)
		self.wTotalLength = subordinate_length + self.DESCRIPTOR_FORMAT.sizeof()

class DescriptorContextManager:
	ParentDescriptor = ComplexDescriptorEmitter
	DescriptorEmitter = None

	def __init__(self, parentDesc : ParentDescriptor):
		self._parent = parentDesc
		self._descriptor = self.DescriptorEmitter()

	def __enter__(self):
		return self._descriptor

	def __exit__(self, exc_type, exc_value, traceback):
		# If an exception was raised, fast exit
		if not (exc_type is None and exc_value is None and traceback is None):
			return
		self._parent.add_subordinate_descriptor(self._descriptor)

class HeaderDescriptor(DescriptorContextManager):
	ParentDescriptor = InterfaceAssociationDescriptorEmitter
	DescriptorEmitter = HeaderDescriptorEmitter

	def __init__(self, parentDesc : InterfaceAssociationDescriptorEmitter):
		super().__init__(parentDesc)
		self._descriptor._parent = parentDesc

class InputTerminalDescriptor(DescriptorContextManager):
	ParentDescriptor = HeaderDescriptorEmitter
	DescriptorEmitter = lambda self: InputTerminalDescriptorEmitter()

class OutputTerminalDescriptor(DescriptorContextManager):
	ParentDescriptor = HeaderDescriptorEmitter
	DescriptorEmitter = lambda self: OutputTerminalDescriptorEmitter()

class FeatureUnitDescriptor(DescriptorContextManager):
	ParentDescriptor = HeaderDescriptorEmitter

	def __init__(self, parentDesc : HeaderDescriptorEmitter, channels : AudioChannels):
		if channels == AudioChannels.MONO:
			self.DescriptorEmitter = lambda: ConstructEmitter(MonoFeatureUnitDescriptor)
		else:
			self.DescriptorEmitter = lambda: ConstructEmitter(StereoFeatureUnitDescriptor)
		super().__init__(parentDesc)

def ConnectorDescriptorEmitter():
	from .descriptors import ConnectorDescriptor
	return ConstructEmitter(ConnectorDescriptor)

class ConnectorDescriptor(DescriptorContextManager):
	ParentDescriptor = HeaderDescriptorEmitter
	DescriptorEmitter = lambda self: ConnectorDescriptorEmitter()
