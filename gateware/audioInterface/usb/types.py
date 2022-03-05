from usb_protocol.emitters.descriptors.standard import InterfaceAssociationDescriptorEmitter
from usb_protocol.emitters.descriptors.uac3 import OutputTerminalDescriptorEmitter

__all__ = (
	'OutputTerminalDescriptor',
)

class OutputTerminalDescriptor:
	def __init__(self, interfaceDesc : InterfaceAssociationDescriptorEmitter):
		self._parent = interfaceDesc
		self._descriptor = OutputTerminalDescriptorEmitter()

	def __enter__(self):
		return self._descriptor

	def __exit__(self):
		self._parent.add_subordinate_descriptor(self._descriptor)
