# Makefile for dependencies.
#
# For Linux OS distribution packages add dependencies to linux_pkg_deps.conf.
# See that file for details on how to use.
#
# For dependencies that need to be built locally do the following.
# (1) Add a subdirectory for the local build and add it to PROJECT_DEPS.
# (2) Add scripts to subdirectory. At a minimum you should create:
#     - build.sh: This is run under your credentials so no sudo please.
#       This script should sheckout code and build locally. Exit 1 on failure.
#     - install.sh: This is run as root. Please do not create files in the
#       build tree with this script. Exit 1 on failure.
#     - check.sh: This is run under your credentials. It should exit 0 is 
#       the dependency is installed or exit 1 if not installed.
# (3) Optionally add common.sh script for common environment settings across
#     build, install, and check.
#
# The scripts (build.sh,check.sh,common,sh,install.sh) are included into
# the local dependency handler build-tool.sh. These scripts should not be 
# executable or have a shabang at the file header. The following environment
# variables are defined in all scripts:
# (1) SCRIPTPATH: absolute path to directory containing scripts.
# (2) ROOTPATH: absolute path to this directory. 
#
# Copyright (c) 2016, Paul Glendenning
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# *** Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
# *** Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
# *** Neither the name of the author nor the names of other contributors may be
#     used to endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

ifeq "$(findstring Darwin,$(shell python -mplatform))" "Darwin"
LINUX=0
ifeq "$(USER)" "$(shell stat /usr/local/bin | awk '{ print $$5}')"
# On OSX homebrew can set owner to a single user
$(info OSX local install for $(USER) only)
SUDO=
else
$(info OSX system install for all users)
SUDO=sudo
endif
ifeq "$(findstring brew,$(shell which brew))" "brew"
OSXBREW=1
OSXPORTS=0
else
OSXBREW=0
ifeq "$(findstring port,$(shell which port))" "port"
OSXPORTS=1
else
OSXPORTS=0
$(error Cannot find OSX package manager brew|ports)
endif
endif
else
$(info Linux install for all users)
LINUX=1
OSXPORTS=0
OSXBREW=0
SUDO=sudo
endif

# Any dependencies that need to be built locally should be added to this list.
ifeq ($(LINUX),1)
PROJECT_DEPS := java protoc protocbuf_py protocbuf_java grpc
else
PROJECT_DEPS := protoc protocbuf_py protocbuf_java grpc
endif

INSTALL_TEMPLATE = @if ./build-tool.sh $(1) check; then \
		echo "$(1) Already installed"; else \
		./build-tool.sh $(1) build && \
		$(SUDO) ./build-tool.sh $(1) install; \
		[ "x$(SUDO)" = "x" ] || $(SUDO) ldconfig; \
		if ./build-tool.sh $(1) check; then \
			echo "$(1) install successful"; else \
			echo "$(1) install failed"; fi; \
		fi

FORCE_INSTALL_TEMPLATE = $(SUDO) ./build-tool.sh $(1) install

CLEAN_TEMPLATE = ./build-tool.sh $(1) clean

BUILD_TEMPLATE = ./build-tool.sh $(1) build

.PHONY: all install-deps install force-install force-build clean

CLEAN_TARGETS=$(addprefix clean-, $(PROJECT_DEPS))
BUILD_TARGETS=$(addprefix build-, $(PROJECT_DEPS))
INSTALL_TARGETS=$(addprefix install-, $(PROJECT_DEPS))
FORCE_INSTALL_TARGETS=$(addprefix force-install-, $(PROJECT_DEPS))
LIST_TARGETS=$(addprefix list-, $(PROJECT_DEPS))

all: install-pkgs install

$(INSTALL_TARGETS):
	@echo "--$@-begin--"
	$(call INSTALL_TEMPLATE, $(patsubst install-%,%,$@))
	@echo "--$@-end--"
	@echo

$(FORCE_INSTALL_TARGETS):
	@echo "--$@-begin--"
	$(call FORCE_INSTALL_TEMPLATE, $(patsubst force-install-%,%,$@))
	@echo "--$@-end--"
	@echo

$(CLEAN_TARGETS):
	@echo "--$@-begin--"
	$(call CLEAN_TEMPLATE, $(patsubst clean-%,%,$@))
	@echo "--$@-end--"
	@echo

$(BUILD_TARGETS):
	@echo "--$@-begin--"
	$(call BUILD_TEMPLATE, $(patsubst build-%,%,$@))
	@echo "--$@-end--"
	@echo

$(LIST_TARGETS):
	@echo "--$@-begin--"
	@ls -lta $(patsubst list-%,installers/%,$@)
	@echo "--$@-end--"
	@echo

# This should be run first
install-pkgs:
ifeq ($(OSXBREW),1)
	$(SUDO) ./install-osx-brew-pkgs.sh
else
ifeq ($(OSXPORTS),1)
	$(SUDO) ./install-osx-macports-pkgs.sh
else
	# will sudo if required
	./pkg-installer.py -iv linux_pkg_deps.conf
endif
endif
ifeq ($(LINUX),1)
	if python -c "import sys;print sys.version" | grep -i 'anaconda\|continuum' >/dev/null 2>/dev/null; \
		then if which python | grep '^$(HOME)'; \
			then ./pkg-installer.py -iv --noroot python_deps.conf; \
			else ./pkg-installer.py -iv python_deps.conf; \
			fi; \
		else ./pkg-installer.py -iv python_deps.conf; \
		fi
endif

install: $(INSTALL_TARGETS)

force-install: $(FORCE_INSTALL_TARGETS)

clean: $(CLEAN_TARGETS)

force-build: $(BUILD_TARGETS)
	
list: $(LIST_TARGETS)	


