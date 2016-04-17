/*
 * Add-ons to binder
 * David Wu
 *
 *
*/

#include <linux/module.h>
#include <linux/kernel.h>

#include "binder_filter.h"

static int binder_filter_enable = 0;
module_param_named(filter_enable, binder_filter_enable, int, S_IWUSR | S_IRUGO);

int filter_binder_message(int type, unsigned long addr, signed long size);
EXPORT_SYMBOL(filter_binder_message);



int filter_binder_message(int type, unsigned long addr, signed long size)
{
	int i;
	int val;
	char* addr_p;
	char buffer[size+1];
	int c = 0;

	//printk(KERN_INFO "BINDERFILTER: type: %d, addr: %08lx, size: %ld\n", type, addr, size);

	if (binder_filter_enable == 1) {
		addr_p = (char*)addr;

		for (i=0; i<size; i++) {
			val = *(addr_p+i);
			if ((val >= 32) && (val <= 126)) {
				buffer[c++] = (char)val;
			}  
		}

		buffer[c] = '\0';
		printk(KERN_INFO "BINDERFILTER: %s\n", buffer);
	}

	return 0;
}


static int __init binder_filter_init(void)
{
	printk(KERN_INFO "BINDERFILTER: started!\n");
	return 0;
}

static void __exit binder_filter_exit(void)
{

}

module_init(binder_filter_init);
module_exit(binder_filter_exit);

MODULE_AUTHOR("David Wu <davidxiaohanwu@gmail.com>");
MODULE_DESCRIPTION("binder filter");
MODULE_LICENSE("GPL v2");