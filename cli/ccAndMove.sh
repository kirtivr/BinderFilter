export PATH=/home/dwu/android-toolchain-16/bin:$PATH
export CC=arm-linux-androideabi-gcc
$CC -fPIE -pie -o middleware middleware.c
adb push middleware sdcard/
adb shell "su -c 'mv sdcard/middleware /data/local/tmp'"
adb shell "su -c 'chmod +x /data/local/tmp/middleware'"