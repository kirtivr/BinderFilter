/*
 * Add-ons to binder
 * David Wu
 *
 *
*/

#ifndef _LINUX_BINDER_FILTER_H
#define _LINUX_BINDER_FILTER_H

enum {
	BF_VERDICT_POSITIVE = 42,
};

enum {
	BF_RETURN_NORMAL = 0,
	BF_RETURN_DROP = 1,
};

enum {
	BF_MESSAGE_TYPE_READ = 0,
	BF_MESSAGE_TYPE_WRITE = 1,
};

struct filter_verdict {
	int result; 			// 1 if we need to act upon the filter
	void* addr;
	void* change;
};


#endif /* _LINUX_BINDER_FILTER_H */