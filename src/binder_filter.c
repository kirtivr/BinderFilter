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

#include "binder_filter.h"
#include "binder.h"

#define MAX_BUFFER_SIZE 500
#define BUFFER_LOG_SIZE 64

static int binder_filter_enable = 0;
module_param_named(filter_enable, binder_filter_enable, int, S_IWUSR | S_IRUGO);

int filter_binder_message(int type, unsigned long addr, signed long size, struct filter_verdict* fv);
EXPORT_SYMBOL(filter_binder_message);



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


/* returns 1 if is little endian */
static int is_little_endian(void) 
{
	int n = 1;
	return *(char *)&n;
}

static int get_int32(char* buf) 
{
	int num = 0;

	if (is_little_endian()) {
		num = buf[0] + (buf[1] << 8) + (buf[2] << 16) + (buf[3] << 24);
	} else {
		num = (buf[0] << 24) + (buf[1] << 16) + (buf[2] << 8) + buf[3];
	}

	return num;
}

// static char* get_string(const char* buf, size_t data_size) 
// {
// 	char* string; 
// 	int i;
// 	char val;
// 	int c = 0;

// 	if (data_size < 0) {
// 		data_size = 0;	// falls through to if (data_size == 0)
// 	}

// 	string = kzalloc(data_size+1, GFP_KERNEL);
//  if (string == NULL) {
// 	    return NULL;
//  }

// 	if (buf <= 0 || data_size == 0) {
// 		string[0] = '\0';
// 		return string;
// 	}

// 	for (i=0; i<data_size; i++) {
// 		val = *(buf+i);
// 		if ((val >= 32) && (val <= 126)) {
// 			string[c++] = (char)val;
// 		}  
// 	}

// 	string[c] = '\0';

// 	kfree(string);
// 	return string;
// }

static void print_string(const char* buf, size_t data_size, char **level_location) 
{
	int i;
	char val;
	int c = 0;
	int len = data_size;
	char* buffer;
	char temp[4];
	const char* level = "level";
	const char* battery = "android.intent.action.BATTERY_CHANGED";

	if (buf <= 0 || data_size <= 0) {
		printk(KERN_INFO "BINDERFILTER: buffer contents: (null)\n");
		return;
	}

	if (data_size > MAX_BUFFER_SIZE) {
		printk(KERN_INFO "BINDERFILTER: data size %d too large (max size %d)", data_size, MAX_BUFFER_SIZE);
		len = MAX_BUFFER_SIZE;
	}

	buffer = (char*) kzalloc(MAX_BUFFER_SIZE*5+1, GFP_KERNEL);
	if (buffer == NULL) {
		return;
	}

	for (i=0; i<len; i++) {
		val = *(buf+i);
		if ((val >= 32) && (val <= 126)) {
			buffer[c++] = (char)val;
		} else if ((int)val > 0) {
			buffer[c++] = '(';

			snprintf(temp, 4, "%d", (int)val);
			buffer[c++] = temp[0];
			if (temp[1] != '\0') { buffer[c++] = temp[1]; }
			if (temp[2] != '\0') { buffer[c++] = temp[2]; }
			
			buffer[c++] = ')';
		}
	}

	buffer[c] = '\0';
	buffer[MAX_BUFFER_SIZE] = '\0';

	printk(KERN_INFO "BINDERFILTER: buffer contents: {%s}\n", buffer);


	if (level_location != NULL) {
		if (strlen(buffer) > strlen(battery) && strstr(buffer, battery) != NULL && strstr(buffer, level) != NULL) {
			*level_location = strstr(buf, level);
			printk(KERN_INFO "BINDERFILTER: match 1 %p\n", *level_location);
			if (level_location != NULL && *level_location != NULL) {
				printk(KERN_INFO "BINDERFILTER: match 2 %p\n", *level_location);
				// *level_location += strlen(level) + sizeof(int);
			}
		}
	} else {
		printk("BINDERFILTER: level location null");
	}


	kfree(buffer);

	return;
}


static void print_binder_transaction_data(struct binder_transaction_data* tr, struct filter_verdict* fv) 
{
	char* level_location = NULL;
#ifdef BF_SEQ_FILE_OUTPUT
	struct bf_buffer_log_entry *e;
	void* buf_copy;
	int size_copy = MAX_BUFFER_SIZE;
#endif

	if (tr <= 0) {
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

	printk(KERN_INFO "BINDERFILTER: data");
	print_string(tr->data.ptr.buffer, tr->data_size, &level_location);	

	// if (level_location != NULL) {
	// 	printk(KERN_INFO "BINDERFILTER: assigning filter_verdict, addr: %p, val %c", tr->data.ptr.offsets, *level_location);

	// 	fv->result = BF_VERDICT_POSITIVE;
	// 	fv->addr = (void*)(level_location);
	// 	fv->change = level_location;

	// 	return;
	// }

	level_location = NULL;

	printk(KERN_INFO "BINDERFILTER: offsets");
	print_string(tr->data.ptr.offsets, tr->offsets_size, &level_location);


#ifdef BF_SEQ_FILE_OUTPUT
	if (tr->data_size < MAX_BUFFER_SIZE) {
		size_copy = tr->data_size;
	}
	buf_copy = (void*) kzalloc(size_copy+1, GFP_KERNEL);
	if (buf_copy == NULL) {
		return;
	}

	e = bf_buffer_log_add(&bf_buffer_log_instance);
	memcpy(buf_copy, tr->data.ptr.buffer, size_copy);
	e->addr = buf_copy;
	e->len = tr->data_size;
#endif

	return;
}

/*
 * message marshalling at: 
 * http://androidxref.com/6.0.1_r10/xref/frameworks/native/libs/binder/IPCThreadState.cpp#904 and #139
 * order: [int32_t cmd, binder_transaction_data tr]
 */
static void unmarshall_message(char* message, signed long size, struct filter_verdict* fv) 
{
	int cmd;
	struct binder_transaction_data* tr_p;

	if (message <= 0 || size <= 0) {
		return;
	}

	cmd = get_int32(message);
	
	switch (cmd) {
	case BC_TRANSACTION:
		printk(KERN_INFO "BINDERFILTER: BC_TRANSACTION\n");
		break;

	case BC_REPLY:
		printk(KERN_INFO "BINDERFILTER: BC_REPLY\n");
		break;

	case BR_TRANSACTION:
		printk(KERN_INFO "BINDERFILTER: BR_TRANSACTION\n");
		break;

	case BR_REPLY:
		printk(KERN_INFO "BINDERFILTER: BR_REPLY\n");
		break;

	default:
		printk(KERN_INFO "BINDERFILTER: bad command received in unmarshall_message!");
		return;
	}

	tr_p = (struct binder_transaction_data *)(message+4);
	print_binder_transaction_data(tr_p, fv);
}

int filter_binder_message(int type, unsigned long addr, signed long size, struct filter_verdict* fv)
{
	int i;
	int val;
	char* addr_p;

	if (addr <= 0 || size <= 0) {
		return -1;
	}

	if (binder_filter_enable == 1) {
		addr_p = (char*)addr;

		for (i=0; i<size/4; i++) {
			val = get_int32(addr_p+(i*4));
			//printk(KERN_INFO "%d", val);

			if (val == BR_TRANSACTION || val == BR_REPLY || 
				val == BC_TRANSACTION || val == BC_REPLY) {
				unmarshall_message(addr_p+(i*4), size, fv);
				return 1;
			}
		}

		// get to here means couldn't find a BR/BC command in the buffer
		//printk(KERN_INFO "BINDERFILTER: error, couldn't find command!");
	}

	return 0;
}


static int __init binder_filter_init(void)
{
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

	printk(KERN_INFO "BINDERFILTER: started.\n");
	return 0;
}

static void __exit binder_filter_exit(void)
{
	printk(KERN_INFO "BINDERFILTER: exited.\n");
}

module_init(binder_filter_init);
module_exit(binder_filter_exit);

MODULE_AUTHOR("David Wu <davidxiaohanwu@gmail.com>");
MODULE_DESCRIPTION("binder filter");
MODULE_LICENSE("GPL v2");