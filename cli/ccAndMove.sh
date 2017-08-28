export PATH=/home/kiwi-the-worst/Documents/bf_stuff/toolchain/bin:$PATH
export ARCH=arm64
export CC=aarch64-linux-android-gcc
$CC -fPIE -pie -o middleware middleware.c
adb push middleware sdcard/
adb root
adb shell "mv sdcard/middleware /data/local/tmp"
adb shell "chmod +x /data/local/tmp/middleware"
