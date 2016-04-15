#include <stdio.h>
#include <stdlib.h>


int main() 
{
	int size = 12;
	char *str = (char*) malloc(size*sizeof(char));
	unsigned long str_ul = (unsigned long)str;
	char* str_p = (char*)str_ul;
	char mesg[size+1];


	unsigned long i;
	int val;
	int cval;
	int count = 0;

	for (i=0; i<size; i++) {
		val = *(str_p+i);
		if ((val >= 32) && (val <= 126)) {
			mesg[count++] = (char)val;
			printf("%d\n", val);
		} else {
			//printf("here");
		}
	}

	mesg[count+1] = '\0';
	printf("%s\n", mesg);
	return 0;
}