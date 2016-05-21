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

/*
    public static final int BLOCK_ACTION = 1;
    public static final int UNBLOCK_ACTION = 2;
    public static final int MODIFY_ACTION = 3;
    public static final int UNMODIFY_ACTION = 4;
*/
enum {
    BLOCK_ACTION = 1,
    UNBLOCK_ACTION = 2,
    MODIFY_ACTION = 3,
    UNMODIFY_ACTION = 4,
};

// what the user passes in
struct bf_user_filter {
	int action;
    int uid;
    char* message;
    char* data;
};

// what we use in the kernel
struct bf_filter_rule {
	int uid;
	char* message;
	int block_or_modify;
	char* data;

	struct bf_filter_rule* next;
};

struct bf_filters {
	int num_filters;
	struct bf_filter_rule* filters_list_head;
};

enum {
	BF_BLUETOOTH_UNKNOWN = -1,
	BF_BLUETOOTH_OFF = 0,
	BF_BLUETOOTH_ON = 1,
};

struct bf_battery_level_struct {
	int level_value_no_BT;
	int level_value_with_BT;
};

/* current values for different enviornment or sensor data */
struct bf_context_values_struct {
	int bluetooth_enabled;
	char wifi_ssid[33]; 			
	char gps[3];		// there are a lot of problems reducing doubles to 3 bytes... but it's what we're doing for now
};

#endif /* _LINUX_BINDER_FILTER_H */