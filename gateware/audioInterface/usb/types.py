from usb_protocol.emitters.descriptor import ConstructEmitter
from usb_protocol.emitters.descriptors.uac3 import AudioChannels, HeaderDescriptorEmitter
from usb_protocol.contextmgrs.manager import DescriptorContextManager
from .descriptors import *

__all__ = (
	'FeatureUnitDescriptor',
)
class FeatureUnitDescriptor(DescriptorContextManager):
	ParentDescriptor = HeaderDescriptorEmitter

	def __init__(self, parentDesc : HeaderDescriptorEmitter, channels : AudioChannels):
		if channels == AudioChannels.MONO:
			self.DescriptorEmitter = lambda: ConstructEmitter(MonoFeatureUnitDescriptor)
		else:
			self.DescriptorEmitter = lambda: ConstructEmitter(StereoFeatureUnitDescriptor)
		super().__init__(parentDesc)
