/*
 * Add-ons to binder
 * David Wu
 *
*/

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/types.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/debugfs.h>
#include <linux/seq_file.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <asm/uaccess.h>
#include <linux/pid.h>
#include <linux/syscalls.h>
#include <linux/reboot.h>
#include <linux/file.h>

#include "binder_filter.h"
#include "binder.h"

#define MAX_BUFFER_SIZE 500
#define BUFFER_LOG_SIZE 64
#define UID_ALL -2
#define LARGE_BUFFER_SIZE 1024
#define SMALL_BUFFER_SIZE 512

#define READ_SUCCESS 1
#define READ_FAIL 0

static int binder_filter_enable = 1;
module_param_named(filter_enable, binder_filter_enable, int, S_IWUSR | S_IRUGO);

static int binder_filter_block_intents = 1;
module_param_named(filter_block_intents, binder_filter_block_intents, int, S_IWUSR | S_IRUGO);

static int binder_filter_print_buffer_contents = 0;
module_param_named(filter_print_buffer_contents, binder_filter_print_buffer_contents, int, S_IWUSR | S_IRUGO);

int filter_binder_message(unsigned long addr, signed long size, int reply, int euid);
EXPORT_SYMBOL(filter_binder_message);

static struct bf_battery_level_struct battery_level;
static struct bf_filters all_filters = {0, NULL};
static struct bf_context_values_struct context_values = {0,{0},{0}};

static int read_persistent_policy_successful = READ_FAIL;

// #define BF_SEQ_FILE_OUTPUT		// define to use seq_printf, etc

#ifdef BF_SEQ_FILE_OUTPUT
	static struct dentry *bf_debugfs_dir_entry_root;

	#define BF_DEBUG_ENTRY(name) \
	static int bf_##name##_open(struct inode *inode, struct file *file) \
	{ \
		return single_open(file, bf_##name##_show, inode->i_private); \
	} \
	\
	static const struct file_operations bf_##name##_fops = { \
		.owner = THIS_MODULE, \
		.open = bf_##name##_open, \
		.read = seq_read, \
		.llseek = seq_lseek, \
		.release = single_release, \
	}

	struct bf_buffer_log_entry {
		void* addr;
		size_t len;
		int set;
		long num;
	};
	struct bf_buffer_log {
		int next;
		int full;
		struct bf_buffer_log_entry entry[BUFFER_LOG_SIZE];
	};
	static struct bf_buffer_log bf_buffer_log_instance;
	static long numAdded;

	static struct bf_buffer_log_entry *bf_buffer_log_add(struct bf_buffer_log *log)
	{
		struct bf_buffer_log_entry *e;
		e = &log->entry[log->next];

		if (e->addr != 0) {
			kfree(e->addr);
		}

		memset(e, 0, sizeof(*e));
		e->set = 1;
		e->num = numAdded++;

		log->next++;
		if (log->next == ARRAY_SIZE(log->entry)) {
			log->next = 0;
			log->full = 1;
		}
		return e;
	}

static void print_bf_buffer_log_entry(struct seq_file *m,
					struct bf_buffer_log_entry *e)
{
	char* buf = (char*)e->addr;
	int i;
	char val;

	if (e->set == 0) {
		return;
	}
	e->set = 0;

	if (buf <= 0 || e->len <= 0) {
		seq_printf(m, "buffer: (null)\n");
		return;
	} 
	seq_printf(m, "buffer %ld: ", e->num);

	for (i=0; i<e->len; i++) {
		val = *(buf+i);
		if ((val >= 32) && (val <= 126)) {
			seq_printf(m, "%c", (char)val);
		} else if ((int)val != 0) {
			seq_printf(m, "(%d)", (int)val);
		}
	}
	seq_puts(m, "\n");

	kfree(e->addr);	
	e->addr = NULL;
}


static int bf_buffers_show(struct seq_file *m, void *unused)
{
	struct bf_buffer_log *log = m->private;
	int i;

	seq_puts(m, "binder buffers:\n");

	if (log->full) {
		for (i = log->next; i < ARRAY_SIZE(log->entry); i++)
			print_bf_buffer_log_entry(m, &log->entry[i]);
	}
	for (i = 0; i < log->next; i++)
		print_bf_buffer_log_entry(m, &log->entry[i]);
	return 0;

}
BF_DEBUG_ENTRY(buffers);

#endif // BF_SEQ_FILE_OUTPUT

// returns new pointer with new_size size, frees old pointer
static char* bf_realloc(char* oldp, int new_size) 
{
	char* newp;

	if (oldp == NULL || new_size <= 0) {
		return NULL;
	}

	newp = (char*) kzalloc(new_size, GFP_KERNEL);
	strncpy(newp, oldp, strlen(oldp));
	kfree(oldp);
	return newp;
}

// modified from http://www.linuxjournal.com/article/8110?page=0,1
static char* read_file(char *filename, int* success)
{
  int fd;
  char buf[1];
  int result_len = LARGE_BUFFER_SIZE;
  int leeway = 8;
  char* result = (char*) kzalloc(result_len, GFP_KERNEL);
  mm_segment_t old_fs = get_fs();

  strncpy(result, "\0", 1);
  set_fs(KERNEL_DS);

  fd = sys_open(filename, O_RDONLY, 0);
  if (fd >= 0) {
    while (sys_read(fd, buf, 1) == 1) {
      if (strlen(result) > result_len - leeway) {
      	result = bf_realloc(result, result_len * 2);
      }

      strncat(result, buf, 1);
    }
    sys_close(fd);
    *success = READ_SUCCESS;
  } else {
  	//printk(KERN_INFO "BINDERFILTER: read fd: %d\n", fd);
  	*success = READ_FAIL;
  }
  set_fs(old_fs);

  return result;
}

// modified from http://www.linuxjournal.com/article/8110?page=0,1
static void write_file(char *filename, char *data)
{
  struct file *file;
  loff_t pos = 0;
  int fd;
  mm_segment_t old_fs = get_fs();

  set_fs(KERNEL_DS);

  fd = sys_open(filename, O_WRONLY|O_CREAT|O_TRUNC, 0644);
  
  if (fd >= 0) {
    sys_write(fd, data, strlen(data));
    file = fget(fd);
    if (file) {
      vfs_write(file, data, strlen(data), &pos);
      fput(file);
    }
    sys_close(fd);
  } else {
  	printk(KERN_INFO "BINDERFILTER: write fd: %d\n", fd);
  }
  set_fs(old_fs);
}

static int add_to_buffer(char* buffer, int c, char val) 
{
	char temp[4];

	if ((val >= 32) && (val <= 126)) {
		buffer[c++] = (char)val;
	} else if ((int)val >= 0) {
		buffer[c++] = '(';

		snprintf(temp, 4, "%d", (int)val);
		buffer[c++] = temp[0];
		if (temp[1] != '\0') { buffer[c++] = temp[1]; }
		if (temp[2] != '\0') { buffer[c++] = temp[2]; }
		
		buffer[c++] = ')';
	} else if ((int)val < 0) {
		buffer[c++] = '(';
		buffer[c++] = '-';

		snprintf(temp, 4, "%d", (int)val);
		buffer[c++] = temp[0];
		if (temp[1] != '\0') { buffer[c++] = temp[1]; }
		if (temp[2] != '\0') { buffer[c++] = temp[2]; }
		
		buffer[c++] = ')';
	}

	return c;
}

/*
	chars are 16 bits (http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/jni/android_os_Parcel.cpp readString())
*/
static void print_string(const char* buf, size_t data_size, int max_buffer_size) 
{
	int i;
	char val[2];
	int c = 0;
	int len = data_size;
	char* buffer;

	if (buf <= 0 || data_size <= 0) {
		printk(KERN_INFO "BINDERFILTER: buffer contents: (null)\n");
		return;
	}

	if (data_size > max_buffer_size) {
		printk(KERN_INFO "BINDERFILTER: data size %d too large (max size %d)", data_size, max_buffer_size);
		len = max_buffer_size;
	}

	buffer = (char*) kzalloc(max_buffer_size*5+1, GFP_KERNEL);
	if (buffer == NULL) {
		return;
	}

	for (i=0; i<len; i=i+2) {
		val[0] = *(buf+i);
		val[1] = *(buf+i+1);
		c = add_to_buffer(buffer, c, val[0]);

		// for 16 bit chars
		if (val[1] != 0) {		
			c = add_to_buffer(buffer, c, val[1]);
		} 
		// else {
		// 	buffer[c++] = '*';
		// }
	}

	buffer[c] = '\0';
	buffer[max_buffer_size] = '\0';

	printk(KERN_INFO "BINDERFILTER: buffer contents: {%s}\n", buffer);
	kfree(buffer);

	return;
}

/*
{(0)@(30)(0)android.app.IApplicationThread(0)(0)(133)h(127)(07)(13)(0)(0)(0).(0)
android.bluetooth.adapter.action.STATE_CHANGED(0)(0)(0)(0)(255)(255)(16)(0)(255)(255)(255)(255)(05)(05)(05)
(05)(05)(05)(05)(05)(254)(255)(200)(00)BD(20)(00).(00)android.bluetooth.adapter.extra.PREVIOUS_STATE
(00)(00)(10)(00)(11)(0)%(0)
android.bluetooth.adapter.extra.STATE(0)(1)(0)(12)(0)(255)(255)(255)(255)(255)(255)(05)(05)(05)(05)(255)(255)(35)(05)}
*/
static void set_bluetooth_value(char* buffer, char* user_buf_start)
{
	const char* bluetooth_state = "adapter.extra.STATE";
	const char* bluetooth_action = "android.bluetooth.adapter.action.STATE_CHANGED";
	char* state_location;
	int offset;
	int bt_value;

	if (strlen(buffer) > strlen(bluetooth_action) && strstr(buffer, bluetooth_action) != NULL) {
		state_location = strstr(buffer, bluetooth_state);
		if (state_location != NULL) {
			offset = ((state_location-buffer) + 19 + 3) * 2;
			bt_value = (int) *(user_buf_start + offset);

			// http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/bluetooth/BluetoothAdapter.java#168
			if (bt_value == 10) {
				context_values.bluetooth_enabled = BF_BLUETOOTH_OFF;
			} else if (bt_value == 12) {
				context_values.bluetooth_enabled = BF_BLUETOOTH_ON;
			}
		}
	}
}

/*
{(0)@(30)(0)android.app.IApplicationThread(0)(0)(133)h(127)(07)(247)(07)(07)(07)
$(07)android.net.conn.CONNECTIVITY_CHANGE(07)(07)(07)(07)(255)(255)(16)(0)(255)(255)(255)(255)(05)(05)(05)(05)(05)(05)(05)(05)(254)(255)x
(05)BD(45)(05)(11)(0)networkInfo(0)(4)(0)(23)(0)android.net.NetworkInfo(0)(1)(0)(0)(0)
(4)(0)WIFI(0)(0)(0)(0)(0)(0)(9)(0)CONNECTED(0)(9)(0)CONNECTED(0)(0)(0)(1)(0)(0)(0)(255)(255)
(18)(0)"Dartmouth Secure"(0)(0)(11)(0)networkType(0)(1)(0)(1)(0)(13)(0)inetCond}
*/
static void set_wifi_value(char* buffer, char* user_buf_start)
{
	const char* wifi_state = "CONNECTED";
	const char* wifi_action = "android.net.conn.CONNECTIVITY_CHANGE";
	char* state_location;
	int offset;
	int ssid_len;

	if (strlen(buffer) > strlen(wifi_action) && strstr(buffer, wifi_action) != NULL) {
		state_location = strstr(buffer, wifi_state);
		if (state_location != NULL) {
			offset = ((state_location-buffer) + 9+3+9+9) * 2;
			ssid_len = (int) *(user_buf_start + offset);
			ssid_len = ssid_len - 2; 		// remove quotes

			if (ssid_len <= 0) {
				return;
			}
			if (ssid_len > 32) {
				ssid_len = 32;
			}

			strncpy(context_values.wifi_ssid , state_location + 9+3+9+9 + 3, ssid_len);
			context_values.wifi_ssid[ssid_len] = '\0';

			//printk(KERN_INFO "BINDERFILTER: ssid: %s\n", context_values.wifi_ssid);
		}
	}
}

/*
{(0)@(29)(0)android.content.IIntentSender(0)(0)(0)(1)(0)(255)(255)(255)(255)(0)(0)(255)(255)(255)(255)(0)(0)(255)(255)(255)(255)(255)(255)(255)(255)(0)(0)(0)(0)(0)(0)(0)(0)(254)(255)(255)(255)(224)
(4)(0)BNDL(3)(0)8(0)com.google.android.location.internal.EXTRA_LOCATION_LIST(0)(0)(11)(0)(1)(0)(4)(0)
(25)(0)android.location.Location(0)
(7)(0)network(0)
(192)(191)(187)(145)T(1)(0)@
(165)R(132)\(0)(177)(237)(254)(194)<(218)E@y(189)(234)(183)e(18)R(192)(0)(0)(0)(0)(0)(0)(0)(0)(0)(0)(0)(0)(0)(0)(1)(0)u(19)(}

{r*k*(0)*C4(247)(145)T(1)(0)*(0)(29)[(204)(16)*(0)*(177)(27)(17)(231)<(218)E@(246)#(234)(170)e(18)R(192)
(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(0)*(1)*(0)*(182)(243)(6)B@(1)
*/
static void set_gps_value(char* buffer, char* user_buf_start)
{
	const char* gps_state = "network";
	const char* gps_action = "com.google.android.location.internal.EXTRA_LOCATION_LIST";
	const char* gps_action2 = "android.content.IIntentSender";
	char* state_location;
	int offset;
	char float_char_output[8];

	if (strlen(buffer) > strlen(gps_action) && strstr(buffer, gps_action) != NULL && strstr(buffer, gps_action2) != NULL) {
		state_location = strstr(buffer, gps_state);
		if (state_location != NULL) {
			offset = ((state_location-buffer) + 7+1+4+4) * 2;
			
			memcpy(float_char_output, user_buf_start+offset, 8);

			// attempt at floating point math.... not very good
			context_values.gps[0] = float_char_output[5];
			context_values.gps[1] = float_char_output[6];
			context_values.gps[2] = float_char_output[7];

			// for (i=0; i<8; i++) {
			// 	printk(KERN_INFO "BINDERFILTER: {%d}\n", float_char_output[i]);
			// }
			//printk(KERN_INFO "BINDERFILTER: gps: %d %d %d\n", context_values.gps[0], context_values.gps[1], context_values.gps[2]);
		}
	}
}

static void set_context_values(const char* user_buf, size_t data_size, char* ascii_buffer) 
{
	set_bluetooth_value(ascii_buffer, (char*)user_buf);
	set_wifi_value(ascii_buffer, (char*)user_buf);
	set_gps_value(ascii_buffer, (char*)user_buf);
}

static void set_battery_level(const char* user_buf, char* ascii_buffer) 
{
	char context_defined_battery_level;
	char* level_location;
	const char* level = "level";
	const char* battery = "android.intent.action.BATTERY_CHANGED";

	if (strlen(ascii_buffer) > strlen(battery) && strstr(ascii_buffer, battery) != NULL) {
		level_location = strstr(ascii_buffer, level);
		if (level_location != NULL && level_location != NULL) {
			level_location = ((level_location-ascii_buffer)*2) + (5+3)*2 + (char*)user_buf;

			if (context_values.bluetooth_enabled == BF_BLUETOOTH_OFF) {
				context_defined_battery_level = (char)battery_level.level_value_no_BT;
			} else if (context_values.bluetooth_enabled == BF_BLUETOOTH_ON) {
				context_defined_battery_level = (char)battery_level.level_value_with_BT;
			} else {
				context_defined_battery_level = 44;
			}

			memcpy((void*)(level_location), &context_defined_battery_level, sizeof(char));
		}
	}

	return;
}

static void block_intent(char* user_buf, size_t data_size, char* ascii_buffer, const char* intent) 
{
	char* intent_location = strstr(ascii_buffer, intent);

	if (intent_location != NULL) {
		printk(KERN_INFO "BINDERFILTER: blocked intent %s\n", intent);
		memset(user_buf, 0, data_size);
	}
}

/* convert from 16 bit chars and remove non characters for string matching */
static char* get_string_matching_buffer(char* buf, size_t data_size) 
{
	int i;
	char val;
	int c = 0;
	char* buffer;

	if (buf <= 0 || data_size <= 0) {
		return NULL;
	}

	buffer = (char*) kzalloc(data_size+1, GFP_KERNEL);
	if (buffer == NULL) {
		return NULL;
	}

	for (i=0; i<data_size; i=i+2) {
		val = *(buf+i);
		if ((val >= 32) && (val <= 126)) {
			buffer[c++] = (char)val;
		} else {
			buffer[c++] = '*';
		}
	}
	buffer[c] = '\0';

	return buffer;
}

static void apply_filter(char* user_buf, size_t data_size, int euid) 
{
	char* ascii_buffer = get_string_matching_buffer(user_buf, data_size);
	struct bf_filter_rule* rule = all_filters.filters_list_head;

	if (ascii_buffer == NULL) {
		return;
	}

	set_battery_level(user_buf, ascii_buffer);
	set_context_values(user_buf, data_size, ascii_buffer);

	if (binder_filter_block_intents == 1) {
		while (rule != NULL) {
			if (rule->uid == UID_ALL || rule->uid == euid) {
				block_intent(user_buf, data_size, ascii_buffer, rule->message);
			}
			rule = rule->next;
		}
	}

	kfree(ascii_buffer);
}

static void print_binder_transaction_data(char* data, size_t data_size, int euid) 
{
#ifdef BF_SEQ_FILE_OUTPUT
	struct bf_buffer_log_entry *e;
	void* buf_copy;
	int size_copy = MAX_BUFFER_SIZE;
#endif

	if (data <= 0) {
		printk(KERN_INFO "BINDERFILTER: error print_binder_transaction_data: "
			"binder_transaction_data was null");
	}

	printk(KERN_INFO "BINDERFILTER: uid: %d\n", euid);

	printk(KERN_INFO "BINDERFILTER: data");
	print_string(data, data_size, MAX_BUFFER_SIZE);	

	// printk(KERN_INFO "BINDERFILTER: offsets");
	// print_string(tr->data.ptr.offsets, tr->offsets_size);


#ifdef BF_SEQ_FILE_OUTPUT
	if (data_size < MAX_BUFFER_SIZE) {
		size_copy = data_size;
	}
	buf_copy = (void*) kzalloc(size_copy+1, GFP_KERNEL);
	if (buf_copy == NULL) {
		return;
	}

	e = bf_buffer_log_add(&bf_buffer_log_instance);
	memcpy(buf_copy, data, size_copy);
	e->addr = buf_copy;
	e->len = data_size;
#endif

	return;
}

// from http://androidxref.com/kernel_3.14/xref/drivers/staging/android/binder.c#1919
// reply = (cmd == BC_REPLY)
void print_binder_code(int reply) {
	if (reply == 0) {
		printk(KERN_INFO "BINDERFILTER: BC_TRANSACTION\n");
	} else if (reply == 1) {
		printk(KERN_INFO "BINDERFILTER: BC_REPLY\n");
	} else {
		printk(KERN_INFO "BINDERFILTER: bad command received in unmarshall_message (%d)", reply);
	}
}

static void add_filter(int block_or_modify, int uid, char* message, char* data) 
{
	struct bf_filter_rule* rule;

	if (uid == -1 || message == NULL) {
		return;
	}

	rule = (struct bf_filter_rule*) 
						kzalloc(sizeof(struct bf_filter_rule), GFP_KERNEL);
	rule->message = (char*) kzalloc(strlen(message)+1, GFP_KERNEL);
	rule->data = (char*) kzalloc(strlen(data)+1, GFP_KERNEL);

	if (block_or_modify != BLOCK_ACTION) {
		// unimplemented for now
		return;
	}
	
	rule->block_or_modify = block_or_modify;
	rule->uid = uid;

	strncpy(rule->message, message, strlen(message));
	rule->message[strlen(rule->message)] = '\0';

	strncpy(rule->data, data, strlen(data));
	rule->data[strlen(rule->data)] = '\0';

	rule->next = all_filters.filters_list_head;
	all_filters.filters_list_head = rule;
	all_filters.num_filters += 1;

	printk(KERN_INFO "BINDERFILTER: added rule: %d %d %s %s\n", 
		rule->uid, rule->block_or_modify, rule->message, rule->data);
}

static void remove_filter(int block_or_modify, int uid, char* message, char* data) 
{
	struct bf_filter_rule* rule;
	struct bf_filter_rule* prev = NULL;

	if (uid == -1 || message == NULL) {
		return;
	}
	printk(KERN_INFO "BINDERFILTER: remove: %d %d %s %s\n", 
			uid, block_or_modify, message, data);

	rule = all_filters.filters_list_head;

	while (rule != NULL) {
		printk(KERN_INFO "BINDERFILTER: rule: %d, %d, %s, %s\n", 
			rule->uid, rule->block_or_modify, rule->message, rule->data);

		if (rule->uid == uid && 
			rule->block_or_modify == block_or_modify &&
			strcmp(rule->message, message) == 0 &&
			strcmp(rule->data, data) == 0) {

			printk(KERN_INFO "BINDERFILTER: match\n");
			// remove from list
			if (prev == NULL) {
				all_filters.filters_list_head = rule->next;	
			} else {
				prev->next = rule->next;
			}

			kfree(rule->message);
			kfree(rule->data);
			kfree(rule);
			return;
		}

		prev = rule;
		rule = rule->next;
	}
	
	return;
}

static int index_of(char* str, char c, int start) 
{
	int len;
	int i;

	if (str == NULL) {
		return -1;
	}

	len = strlen(str);
	if (start >= len) {
		return -1;
	}

	for (i=start; i<len; i++) {
		if (str[i] == c) {
			return i;
		}
	}

	return -1;
}

static void apply_policy_line(char* policy) 
{
	long action = -1;
	long uid = -1;

	char* action_str = NULL;
	char* uid_str = NULL;
	char* message = NULL;
	char* data = NULL;

	int index;
	int old_index;
	int size;

	printk(KERN_INFO "BINDERFILTER: reading policy: {%s}\n", policy);

	// message
	index = index_of(policy, ':', 0);
	if (index != -1) {
		message = (char*) kzalloc(index+2, GFP_KERNEL);
		strncpy(message, policy, index);
		message[index+1] = '\0';
	}

	// uid
	old_index = index;
	index = index_of(policy, ':', old_index+1);
	size = index - old_index;
	if (index != -1) {
		uid_str = (char*) kzalloc(size+2, GFP_KERNEL);
		strncpy(uid_str, (policy+old_index+1), size-1);
		uid_str[size+1] = '\0';

		if (kstrtol(uid_str, 10, &uid) != 0) {
			printk(KERN_INFO "BINDERFILTER: could not parse uid! {%s}\n", uid_str);
			uid = -1;
		}
	}

	// action
	old_index = index;
	index = index_of(policy, ':', old_index+1);
	size = index - old_index;
	if (index != -1) {
		action_str = (char*) kzalloc(size+2, GFP_KERNEL);
		strncpy(action_str, (policy+old_index+1), size-1);
		action_str[size+1] = '\0';
		
		if (kstrtol(action_str, 10, &action) != 0) {
			printk(KERN_INFO "BINDERFILTER: could not parse action! {%s}\n", action_str);
			action = -1;
		}
	}

	// data, for now
	data = (char*) kzalloc(1, GFP_KERNEL);


	printk(KERN_INFO "BINDERFILTER: parsed policy: {%s} {%d} {%d} \n", 
		message, (int)uid, (int)action);

	if (message != NULL && 
		uid != -1 && action != -1 && 
		data != NULL) {

		add_filter((int)action, (int)uid, message, "");
	} else {
		printk(KERN_INFO "BINDERFILTER: could not parse policy!\n");
	}
	
	if (action_str != NULL) {
		kfree(action_str);
	}
	if (uid_str != NULL) {
		kfree(uid_str);
	}
	if (message != NULL) {
		kfree(message);
	}
	if (data != NULL) {
		kfree(data);
	}

	kfree(policy);
}

static void apply_policy(char* policy) 
{
	char* line;
	int index;
	int old_index = 0;
	int size;

	if (policy == NULL) {
		return;
	}

	while (1) {
		index = index_of(policy, '\n', old_index);
		if (index == -1) {
			return;
		}

		size = index-old_index;
		line = (char*) kzalloc(size+2, GFP_KERNEL);
		strncpy(line, policy+old_index, size);
		line[size] = '\0';
		printk(KERN_INFO "BINDERFILTER: line: {%s}\n", line);

		if (size < 4) {
			return;
		}

		apply_policy_line(line);
		old_index = index + 1;
	}

}

static void read_persistent_policy(void) 
{
	int success = READ_FAIL;
	char* policy;

	policy = read_file("/data/local/tmp/bf.policy", &success);
	read_persistent_policy_successful = success;

	if (success == READ_SUCCESS) {
		apply_policy(policy);
	} 

	kfree(policy);
}

// ENTRY POINT FROM binder.c
// because we're only looking at binder_writes, pid refers to the pid of the writing proc
int filter_binder_message(unsigned long addr, signed long size, int reply, int euid)
{
	if (addr <= 0 || size <= 0) {
		return -1;
	}

	if (binder_filter_enable != 1) {
		return 0;
	}

	// only reads once successfully
	if (read_persistent_policy_successful != READ_SUCCESS) {
		read_persistent_policy();
	}

	if (binder_filter_print_buffer_contents == 1) {
		print_binder_code(reply);
		print_binder_transaction_data((char*)addr, size, euid);
	}
	apply_filter((char*)addr, size, euid);

	return 1;
}

static char* get_policy_string(void)
{
	int policy_str_len_max = LARGE_BUFFER_SIZE;
	int temp_len_max = SMALL_BUFFER_SIZE;
	char *policy_str = (char*) kzalloc(policy_str_len_max, GFP_KERNEL);
	char *temp = (char*) kzalloc(temp_len_max,GFP_KERNEL);
	int policy_str_len;
	int temp_len;
	struct bf_filter_rule* rule;

	rule = all_filters.filters_list_head;
	while (rule != NULL) {
		temp_len = strlen(rule->message) + strlen(rule->data);
		if (temp_len > temp_len_max) {
			temp = bf_realloc(temp, temp_len * 2);
			temp_len_max = temp_len * 2;
		}

		sprintf(temp, "%s:%d:%d:\n", rule->message, rule->uid, rule->block_or_modify);

		policy_str_len = strlen(temp) + strlen(policy_str);
		if (policy_str_len > policy_str_len_max) {
			policy_str = bf_realloc(policy_str, policy_str_len * 2);
			policy_str_len_max = policy_str_len * 2;
		}

		strcat(policy_str, temp);
		rule = rule->next;
	}

	kfree(temp);

	return policy_str;
}

static void init_context_values(void) 
{
	context_values.bluetooth_enabled = BF_BLUETOOTH_UNKNOWN;		
}

static void write_persistent_policy(void) 
{
	char* policy = get_policy_string();
	printk(KERN_INFO "BINDERFILTER: writing policy: {%s}\n", policy);
	write_file("/data/local/tmp/bf.policy", policy);
	kfree(policy);
}

static int bf_open(struct inode *nodp, struct file *filp)
{
	printk(KERN_INFO "BINDERFILTER: opened driver\n");
	return 0;
}

// reports policy info
static ssize_t bf_read(struct file * file, char * buf, size_t count, loff_t *ppos)
{	
	int len;
	char* ret_str;

	// sprintf(ret_str, "BINDERFILTER: bluetooth_enabled: %d, wifi_ssid: %s, gps: {%d,%d,%d}\n", 
	// 	context_values.bluetooth_enabled, context_values.wifi_ssid, 
	// 	context_values.gps[0], context_values.gps[1], context_values.gps[2]);

	// sprintf(temp, "BINDERFILTER: filters:\n");
	// strcat(ret_str, temp);

	ret_str = get_policy_string();
	len = strlen(ret_str); /* Don't include the null byte. */
    
    if (count < len) {
        return -EINVAL;
    }

    if (*ppos != 0) {
        return 0;
    }

    if (copy_to_user(buf, ret_str, len)) {
        return -EINVAL;
    }

    kfree(ret_str);

    *ppos = len;
    return len;
}

static ssize_t bf_write(struct file *file, const char __user *buf, size_t len, loff_t *ppos)
{
	struct bf_user_filter user_filter;

	if (len < 0 || len > 5000 || buf == NULL) {
		printk(KERN_INFO "BINDERFILTER: bf_write bad arguments\n");
		return 0;
	}

	if (copy_from_user(&user_filter, buf, sizeof(user_filter))) {
		printk(KERN_INFO "BINDERFILTER: bf_write copy_from_user failed\n");
		return 0;
	}

	switch (user_filter.action) {
		case BLOCK_ACTION:
			add_filter(BLOCK_ACTION, user_filter.uid, user_filter.message, "");
			break;
		case UNBLOCK_ACTION:
			// pass in BLOCK_ACTION to remove the BLOCK_ACTION rule previously set
			remove_filter(BLOCK_ACTION, user_filter.uid, user_filter.message, user_filter.data);
			break;
		case MODIFY_ACTION:
			//add_filter(MODIFY_ACTION, user_filter.uid, user_filter.message, user_filter.data);
			// fall
		case UNMODIFY_ACTION:
			//remove_filter(MODIFY_ACTION, user_filter.uid, user_filter.message, user_filter.data);
			// fall
		default:
			printk(KERN_INFO "BINDERFILTER: bf_write bad action %d\n", 
				user_filter.action);
			return 0;
	}

	write_persistent_policy();
    return sizeof(user_filter);
}

static const struct file_operations bf_fops = {
	.owner = THIS_MODULE,
	.open = bf_open,
	.read = bf_read,
	.write = bf_write,
};

static struct miscdevice bf_miscdev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "binderfilter",
	.fops = &bf_fops
};

static int __init binder_filter_init(void)
{
	int ret;

#ifdef BF_SEQ_FILE_OUTPUT
	int i;

	bf_debugfs_dir_entry_root = debugfs_create_dir("binder_filter", NULL);
	if (bf_debugfs_dir_entry_root == NULL) {
		printk(KERN_INFO "BINDERFILTER: could not create debugfs entry!");
		return 1;
	}

	debugfs_create_file("buffers",
			    S_IRUGO,
			    bf_debugfs_dir_entry_root,
			    &bf_buffer_log_instance,
			    &bf_buffers_fops);

	for (i=0; i<BUFFER_LOG_SIZE; i++) {
		bf_buffer_log_instance.entry[i].addr = 0;
		bf_buffer_log_instance.entry[i].set = 0;
	}

	numAdded = 0;
#endif

	ret = misc_register(&bf_miscdev);
	if (ret) {
		printk(KERN_INFO "BINDERFILTER: unable to register device, ret %d\n", ret);
		return ret;
	}

	battery_level.level_value_no_BT = 42;
	battery_level.level_value_with_BT = 43;

	init_context_values();

	printk(KERN_INFO "BINDERFILTER: started.\n");
	return 0;
}

device_initcall(binder_filter_init);

MODULE_AUTHOR("David Wu <davidxiaohanwu@gmail.com>");
MODULE_DESCRIPTION("binder filter");
MODULE_LICENSE("GPL v2");