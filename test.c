#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int is_little_endian() 
{
	int n = 1;
	return *(char *)&n;
}

static int get_int32(char* buf) 
{
	int num;

	if (is_little_endian()) {
		num = buf[0] + (buf[1] << 8) + (buf[2] << 16) + (buf[3] << 24);
	} else {
		num = (buf[0] << 24) + (buf[1] << 16) + (buf[2] << 8) + buf[3];
	}

	return num;
}

struct s {
	int a;
	int b;
};

static void dosomething(char** cp) {
	char c = 'c';
	*cp = &c;
}

int main() 
{
	int size = 12;
	char message[4];
	//int num = 127;

	message[0] = 0x00;
	message[1] = 0x00;
	message[2] = 0x72;
	message[3] = 0x0c;

	//printf("%d\n", *((int*)message));
	
	char* m = message;
	printf("%d\n", get_int32(m));

	struct s s1;
	struct s* s1p = &s1;

	struct s s2;
	struct s* s2p = s1p;
	s2 = *s2p;


	const char* str1 = "0123456789";
	const char* str2 = "3456";

	char* loc = NULL;
	dosomething(&loc);
	loc = strstr(str1, str2);
	printf("loc: %p, str1: %p\n", loc, str1);
	




	return 0;
}