# Information Extraction

IE is an information extraction engine that aims to learn textual entailment by 
reading.  It uses a CCG parser to discover the type categories in a sentence and
then builds a discourse representation.

## Overview

- `ext`: external back-end service clients.
  Currently, there is only one back-end service:
  1. "EasySRL" CCG parser.
  
- `deps`: dependencies necessary for compiling IE.
  Due to the fact that services share some common dependencies,
  all services should be compiled after these dependencies are installed.
  
- `src`: common code for gRPC service support.

## Initializing the Build

This must be done once. From the main directory run:
```
cd deps
make
sudo make install
```

This will install all missing dependencies so it may need root access. We assume
your username is in the sudoers list so make sure it is. **Do not** run `make` as
root because this will create a whole bunch of files in the build tree owned by root.

## Large File Support

The model file ares are too large to store directly on github. We use the
[git-lfs extension](https://git-lfs.github.com/) to accommodate large files. 
After the you have installed the dependencies you will need to setup large
file support as described here.

I have done this on home brew and the suggestion is to run the following
commands prior to accessing large files.

```
git lfs install
git lfs install --system
```

After which you must set the file types that are stored in LFS. We are currently
only storing compressed files so run these commands from the top level directory.

```
git lfs track "*.gz"
git lfs track "*.zip"
git lfs track "*.tgz"
git lfs track "*.bz2"
```
    
Finally make sure .gitattributes is tracked

```
git add .gitattributes
```

## Building

- From the root checkout directory, type: `gradle build -x test`. If you 
  want to run unit tests then omit `-x test`. Tests have to load the 
  models so they take about 1.5 minutes to complete.
    - `gradle build`: to build and run tests with minimal output.
    - `gradle build --info`: to build and run tests displaying stdout and log 
       messages during test.
    - `gradle build -x test`: build without running tests.
    - `gradle test [--info]`: just run tests.
    
The EasySRLDaemonTest can take over 30 seconds if an error occurs so use
the `--info`option to see what is happening. 

#### Build Javadocs

Run `gradle alljavadoc`. The docs will be located at build/docs/. 

#### IntelliJ IDEA Integration for Java Code

The root project file [build.gradle](build.gradle) uses the idea plugin.
To create your IDEA project run `gradle idea`. To rebuild the project run
`gradle cleanIdea idea`.

Open IDEA and load the project at the root level. When you open the first
time a warning message will appear saying "unlinked gradle project".
Click on that message and import the gradle project.
 
### Testing

To execute all tests run `gradle build`.  The python tests are also run
as part of the gradle test suite.

## Adding Backend Services

### Java Services Based on External Source

1. Create a new directory under the ext directory. Name it according
   to the service provided. We refer to it as \<service-name\>.
2. Add the build tree for the existing source as a subdir of \<service-name\>.
   Add a build.gradle to this directory.
3. Create a build.gradle file in \<service-name\>. Use the file [ext/build.gradle](ext/build.gradle)
   as a reference.
4. Add the new projects to [settings.gradle](settings.gradle).


For example:
```
ext[+]
    |
    +-- build.gradle
    |
    +-- easysrl [+]- build.gradle  <service-name=easysrl>
    |            |
    |            '-- (external sourcetree)
    |
    +-- src [+] -- main/java/ai/marbles/easysrl [+]
             |                                   |
             |                                   '-- source for EasySRL gRPC service
             |
             '---- test/java/ai/marbles/easysrl [+]
                                                 |
                                                 '-- tests for EasySRL gRPC service
```

### C++ Services Based on Existing Source

Currently we are not using any C++ services. If we need to change this behavior then
copy files from the [eTutor project](https://github.com/marbles-ai/etutor).


# Running the EasySRL service
Not currently working. For the moment run `./ext/daemons/easysrl.sh` in a shell and 
Ctrl-C to exit the service.

IGNORE THIS
- To start the EasySRL CCG parser gRPC service run:
  ```
  ./scripts/start_server.sh ./ext/daemons/easysrl.sh
  ```

  This will spawn a gnu screen for the backend service as well as the 
  web site. To see the list of active screens run `screen -list`. Once
  they all start running,  open your browser and visit `http://localhost:3000/`.
  
- To stop the EasySRL parser service run:
  ```
  ./scripts/stop_server ./ext/daemons/easysrl.sh
  ```

