#!/bin/bash

function brew_install() {
	brew list $1 >/dev/null 2>&1 && return 0
	echo "Installing $1"
	echo brew install $*
	brew install $*
}

# Homebrew installs are local to the current user
brew update
brew_install coreutils
brew_install doxygen
brew_install graphviz

# gRPC
brew_install openssl
brew_install maven
brew_install gradle

# pseudo terminal
brew tap homebrew/dupes
brew_install screen 

# STP
brew_install boost
brew_install boost-python
brew_install bison
brew_install flex
