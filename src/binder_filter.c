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

#include "binder_filter.h"
#include "binder.h"

#define MAX_BUFFER_SIZE 500
#define BUFFER_LOG_SIZE 64

static int binder_filter_enable = 0;
module_param_named(filter_enable, binder_filter_enable, int, S_IWUSR | S_IRUGO);

static int binder_filter_print_buffer_contents = 0;
module_param_named(filter_print_buffer_contents, binder_filter_print_buffer_contents, int, S_IWUSR | S_IRUGO);

int filter_binder_message(unsigned long addr, signed long size, int reply);
EXPORT_SYMBOL(filter_binder_message);

static struct bf_battery_level_struct battery_level;
static struct context_values_struct context_values = {0,0,{0,0,0}};

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
	char* ssid;

	// free prev ssid
	if (context_values.wifi_ssid != NULL) {
		kfree(context_values.wifi_ssid);
		context_values.wifi_ssid = NULL;
	}

	if (strlen(buffer) > strlen(wifi_action) && strstr(buffer, wifi_action) != NULL) {
		state_location = strstr(buffer, wifi_state);
		if (state_location != NULL) {
			offset = ((state_location-buffer) + 9+3+9+9) * 2;
			ssid_len = (int) *(user_buf_start + offset);

			if (ssid_len <= 0 || ssid_len > 256) {
				return;
			}

			ssid = (char*) kzalloc(ssid_len+1, GFP_KERNEL);
			strncpy(ssid, state_location + 9+3+9+9 + 3, ssid_len-2);
			ssid[ssid_len-1] = '\0';
			context_values.wifi_ssid = ssid;

			//printk(KERN_INFO "BINDERFILTER: ssid: %s\n", context_values.wifi_ssid);
		}
	}
}

/*
{(0)@(29)(0)android.content.IIntentSender(0)(0)(0)(1)(0)(255)(255)(255)(255)(0)(0)(255)(255)(255)(255)(0)(0)(255)(255)(255)(255)(255)(255)(255)(255)(0)(0)(0)(0)(0)(0)(0)(0)(254)(255)(255)(255)(224)(4)(0)BNDL(3)(0)8(0)com.google.android.location.internal.EXTRA_LOCATION_LIST(0)(0)(11)(0)(1)(0)(4)(0)(25)(0)android.location.Location(0)
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
			printk(KERN_INFO "BINDERFILTER: gps: %d %d %d\n", context_values.gps[0], context_values.gps[1], context_values.gps[2]);
		}
	}
}

static void set_context_values(const char* buf, size_t data_size) 
{
	int i;
	char val;
	int c = 0;
	int len = data_size;
	char* buffer;

	if (buf <= 0 || data_size <= 0) {
		return;
	}

	buffer = (char*) kzalloc(len+1, GFP_KERNEL);
	if (buffer == NULL) {
		return;
	}

	for (i=0; i<len; i=i+2) {
		val = *(buf+i);
		if ((val >= 32) && (val <= 126)) {
			buffer[c++] = (char)val;
		} else {
			buffer[c++] = '*';
		}
	}
	buffer[c] = '\0';

	set_bluetooth_value(buffer, (char*)buf);
	set_wifi_value(buffer, (char*)buf);
	set_gps_value(buffer, (char*)buf);

	kfree(buffer);
}

//restructure this to be more of a "set_battery level"
static char* filter_string_battery_level(const char* buf, size_t data_size, char **level_location) 
{
	int i;
	char val;
	int c = 0;
	int len = data_size;
	char* buffer;
	const char* level = "level";
	const char* battery = "android.intent.action.BATTERY_CHANGED";

	if (buf <= 0 || data_size <= 0) {
		return NULL;
	}

	buffer = (char*) kzalloc(len+1, GFP_KERNEL);
	if (buffer == NULL) {
		return NULL;
	}

	for (i=0; i<len; i=i+2) {
		val = *(buf+i);
		if ((val >= 32) && (val <= 126)) {
			buffer[c++] = (char)val;
		} else {
			buffer[c++] = '*';
		}
	}
	buffer[c] = '\0';

	if (strlen(buffer) > strlen(battery) && strstr(buffer, battery) != NULL && strstr(buffer, level) != NULL) {
		*level_location = strstr(buffer, level);
		if (level_location != NULL && *level_location != NULL) {
			*level_location = ((*level_location-buffer)*2) + (5+3)*2 + (char*)buf;
			
			kfree(buffer);
			return *level_location;
		}
	}

	kfree(buffer);

	return NULL;
}

static void apply_filter(char* data, size_t data_size) 
{
	char* level_location = NULL;
	char* to_copy = kzalloc(1, GFP_KERNEL);
	int context_defined_battery_level;
	struct filter_verdict *fv = kzalloc(sizeof(struct filter_verdict), GFP_KERNEL);

	level_location = filter_string_battery_level(data, data_size, &level_location);	
	if (level_location != NULL) {
		//printk(KERN_INFO "BINDERFILTER: found match at %p", level_location);

		if (context_values.bluetooth_enabled == BF_BLUETOOTH_OFF) {
			context_defined_battery_level = battery_level.level_value_no_BT;
		} else if (context_values.bluetooth_enabled == BF_BLUETOOTH_ON) {
			context_defined_battery_level = battery_level.level_value_with_BT;
		} else {
			context_defined_battery_level = 44;
		}

		*to_copy = (char)context_defined_battery_level;
		fv->result = BF_VERDICT_POSITIVE;
		fv->addr = (void*)(level_location);
		fv->change = to_copy;
	}

	if (fv->result == BF_VERDICT_POSITIVE) {
		//printk(KERN_INFO "BINDERFILTER: verdict positive!\n");

		memcpy(fv->addr, fv->change, sizeof(char));
	}

	kfree(fv->change);
	kfree(fv);

	set_context_values(data, data_size);
}

static void print_binder_transaction_data(char* data, size_t data_size) 
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
	
	// printk(KERN_INFO "BINDERFILTER: binder_transaction_data: target handle: %d, "
	// 	"target ptr: %p, target cookie: %p, transaction code: %d, "
	// 	"flags: %d, sender_pid: %d, sender_euid: %d, data_size: %d, "
	// 	"offsets_size: %d, data.ptr.buffer: %p, data.ptr.offsets: %p",
	// 	tr->target.handle, tr->target.ptr, tr->cookie, tr->code, 
	// 	tr->flags, tr->sender_pid, tr->sender_euid, tr->data_size,
	// 	tr->offsets_size, tr->data.ptr.buffer, tr->data.ptr.offsets);

	if (binder_filter_print_buffer_contents == 1) {
		printk(KERN_INFO "BINDERFILTER: data");
		print_string(data, data_size, MAX_BUFFER_SIZE);	
	}

	if (binder_filter_print_buffer_contents == 1) {
		// printk(KERN_INFO "BINDERFILTER: offsets");
		// print_string(tr->data.ptr.offsets, tr->offsets_size);
	}

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

int filter_binder_message(unsigned long addr, signed long size, int reply)
{
	

	if (addr <= 0 || size <= 0) {
		return -1;
	}

	if (binder_filter_enable != 1) {
		return 0;
	}

	if (binder_filter_print_buffer_contents == 1) {
		print_binder_code(reply);
		print_binder_transaction_data((char*)addr, size);
	}
	apply_filter((char*)addr, size);

	return 1;
}

static void init_context_values(void) 
{
	context_values.bluetooth_enabled = BF_BLUETOOTH_UNKNOWN;		
}

static int bf_open(struct inode *nodp, struct file *filp)
{
	printk(KERN_INFO "BINDERFILTER: bf_open");
	return 0;
}

// reports policy info
static ssize_t bf_read(struct file * file, char * buf, size_t count, loff_t *ppos)
{
	char *ret_str = (char*)kzalloc(100, GFP_KERNEL);
	int len;

	sprintf(ret_str, "BINDERFILTER: battery level no BT: %d, battery level with BT: %d\n", 
		battery_level.level_value_no_BT, battery_level.level_value_with_BT);

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

	if (len < 0 || len > 1000 || buf == NULL) {
		printk(KERN_INFO "BINDERFILTER: bf_write bad arguments\n");
		return 0;
	}

	if (copy_from_user(&user_filter, buf, sizeof(user_filter))) {
		printk(KERN_INFO "BINDERFILTER: bf_write copy_from_user failed\n");
		return 0;
	}

    printk("BINDERFILTER: in bf_write, with values %d %d\n", 
    	user_filter.level_value_no_BT, user_filter.level_value_with_BT);

    if (user_filter.level_value_no_BT != -1) {
    	battery_level.level_value_no_BT = user_filter.level_value_no_BT;
    }
    if (user_filter.level_value_with_BT != -1) {
    	battery_level.level_value_with_BT = user_filter.level_value_with_BT;
    }

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