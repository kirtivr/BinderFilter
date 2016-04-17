/*
 * Add-ons to binder
 * David Wu
 *
 *
*/

#ifndef _LINUX_BINDER_FILTER_H
#define _LINUX_BINDER_FILTER_H

enum {
	BF_RETURN_NORMAL = 0,
	BF_RETURN_DROP = 1,
};

enum {
	BF_MESSAGE_TYPE_READ = 0,
	BF_MESSAGE_TYPE_WRITE = 1,
};

#endif /* _LINUX_BINDER_FILTER_H */