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

# GIT-HUB Large File Support
brew_install git-lfs

# Java
if [ "x`which java`" == "x" ]; then
	brew cask install java
else
	# check version
	JAVAVER="`java -version 2>&1 | grep 'java version' | sed 's/^.*"\([0-9.]*\)\.[0-9]_.*".*$/\1/g' | sed 's/\./0/g'`"
	if [ "x$JAVAVER" != "x" ]; then
		if [ $JAVAVER -lt 108 ]; then
			brew cask install java
		fi
	fi
fi

# Z3 prover
# 	--with-python3 for py3 bindings
# 	--without-python to remove py2 bindings
brew_install z3
