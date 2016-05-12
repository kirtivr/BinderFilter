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

struct filter_verdict {
	int result; 			// 1 if we need to act upon the filter
	void* addr;
	void* change;
};

struct bf_user_filter {
	int level_value_no_BT;
	int level_value_with_BT;

	char** intents;
	int intents_len;
};

struct bf_battery_level_struct {
	int level_value_no_BT;
	int level_value_with_BT;
};

struct intent_struct {
	char** intents;
	int intents_len;
};

enum {
	BF_BLUETOOTH_UNKNOWN = -1,
	BF_BLUETOOTH_OFF = 0,
	BF_BLUETOOTH_ON = 1,
};

/* current values for different enviornment or sensor data */
struct context_values_struct {
	int bluetooth_enabled;
	char wifi_ssid[33]; 			
	char gps[3];		// there are a lot of problems reducing doubles to 3 bytes... but it's what we're doing for now
};

#endif /* _LINUX_BINDER_FILTER_H */