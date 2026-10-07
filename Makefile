PACKAGE_VERSION = 1.3.0
ifeq ($(THEOS_PACKAGE_SCHEME),roothide)
PACKAGE_VERSION = 1.3.0-1+native1
# RootHide uses the modern arm64e ABI, not the legacy Xcode 11 toolchain.
# Pin compilation and linking to the downloaded SDK, never the runner's latest.
override TARGET = iphone:clang:16.5:15.0
override ARCHS = arm64e
else ifeq ($(THEOS_PACKAGE_SCHEME),rootless)
TARGET = iphone:clang:latest:14.0
ARCHS = arm64 arm64e
else
TARGET = iphone:clang:14.5:9.0
export PREFIX = $(THEOS)/toolchain/Xcode11.xctoolchain/usr/bin/
endif

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = LetMeBlock
$(TWEAK_NAME)_FILES = Tweak.xm
$(TWEAK_NAME)_LIBRARIES = sandy
$(TWEAK_NAME)_CFLAGS = -fobjc-arc

ifeq ($(THEOS_PACKAGE_SCHEME),roothide)
$(TWEAK_NAME)_LIBRARIES += roothide
$(TWEAK_NAME)_FRAMEWORKS += Foundation
# Optional verified prebuilt dependency locations; normal Theos paths also work.
ifneq ($(strip $(LMB_LIBSANDY_INCLUDE_DIR)),)
$(TWEAK_NAME)_CFLAGS += -I$(LMB_LIBSANDY_INCLUDE_DIR)
endif
ifneq ($(strip $(LMB_LIBSANDY_LIB_DIR)),)
$(TWEAK_NAME)_LDFLAGS += -L$(LMB_LIBSANDY_LIB_DIR)
endif
endif

include $(THEOS_MAKE_PATH)/tweak.mk

ifeq ($(THEOS_PACKAGE_SCHEME),roothide)
LMB_PYTHON ?= python3
after-stage::
	$(LMB_PYTHON) "$(THEOS_PROJECT_DIR)/scripts/stage_native.py" --project "$(THEOS_PROJECT_DIR)" --stage "$(THEOS_STAGING_DIR)" --payload

# Theos generates DEBIAN/control as a before-package prerequisite.
before-package::
	$(LMB_PYTHON) "$(THEOS_PROJECT_DIR)/scripts/stage_native.py" --project "$(THEOS_PROJECT_DIR)" --stage "$(THEOS_STAGING_DIR)" --control
endif
