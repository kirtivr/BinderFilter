#!/bin/bash

echo "remember to call me as source compileModules.sh"

export ARCH=arm
export SUBARCH=arm
export CROSS_COMPILE=arm-eabi-
export PATH=/media/sf_sharedVm/arm-eabi-4.6/libexec:/media/sf_sharedVm/arm-eabi-4.6/bin:$PATH
cd /media/sf_msm/
make flo_defconfig
make prepare
echo "CONFIG_MODULES=y" | cat >> .config
echo "CONFIG_MODULE_FORCE_LOAD=y" | cat >> .config
echo "CONFIG_MODULE_UNLOAD=y" | cat >> .config
echo "CONFIG_MODULE_FORCE_UNLOAD=y" | cat >> .config
echo "CONFIG_MODVERSIONS=y" | cat >> .config
echo "CONFIG_ANDROID_BINDER_FILTER=y" | cat >> .config
make modules_prepare
#make ARCH=arm CONFIG_HELLOWORLD=m M=drivers/helloworld
#make ARCH=arm CONFIG_ANDROID_BINDER_FILTER=m M=drivers/staging/android