export PATH=/home/kiwi-the-worst/Documents/BinderFilter/resources/android-toolchain-16/bin:$PATH
export CC=arm-linux-androideabi-gcc
$CC -fPIE -pie -o middleware middleware.c
adb push middleware sdcard/
adb shell "su 'mv sdcard/middleware /data/local/tmp'"
adb shell "su 'chmod +x /data/local/tmp/middleware'"
