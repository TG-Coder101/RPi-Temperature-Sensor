#include <linux/module.h>
#include <linux/init.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>
#include <linux/device.h>
#include <linux/uaccess.h>
#include <linux/fs.h>
#include <linux/spinlock.h>
#define DEVICE_NAME "tempchar"
#define CLASS_NAME "temp"

/* Meta Information */
MODULE_LICENSE("GPL");
MODULE_AUTHOR("");
MODULE_DESCRIPTION("An LKM for a gpio interrupt that lights up an LED");
MODULE_VERSION("0.1");

static unsigned int Led = 16;
static unsigned int Button = 17;
static unsigned int counter = 0;
static bool state = 0;
/* variable contains pin number interrupt controller to which GPIO 17 is mapped to */
static unsigned int irq_number;
static bool buttonPress;
/* spinlock to syncronise access to buttonPress */
DEFINE_SPINLOCK(defLock);

extern unsigned long volatile jiffies;
unsigned long old_jiffie = 0;

static int majorNumber;
static struct class* tempcharClass = NULL;
static struct device* tempcharDevice = NULL;

// The prototype functions for the character driver -- must come before the struct definition
static int     dev_open(struct inode *, struct file *);
static int     dev_release(struct inode *, struct file *);
static ssize_t dev_read(struct file *, char *, size_t, loff_t *);
static ssize_t dev_write(struct file *, const char *, size_t, loff_t *);
 
/** @brief Devices are represented as file structure in the kernel. The file_operations structure from
 *  /linux/fs.h lists the callback functions that you wish to associated with your file operations
 *  using a C99 syntax structure. char devices usually implement open, read, write and release calls
 */
static struct file_operations fops =
{
    .open = dev_open,
    .read = dev_read,
    .write = dev_write,
    .release = dev_release,
};

/**
 * @brief Interrupt service routine is called when the interrupt is triggered
 */
static irq_handler_t gpio_irq_handler(unsigned int irq, void *dev_id, struct pt_regs *regs) {
    printk("gpio_irq: Interrupt was triggered and ISR was called!\n");
     	
    unsigned long diff = jiffies - old_jiffie;
    if (diff < 20) {
    	return (irq_handler_t) IRQ_HANDLED;
    }	
    
    state = !state; /* Toggle LED */
    if (state){
    	gpio_set_value(Led, 1);	
    }
    else {
    	gpio_set_value(Led, 0);
    }
    
    spin_lock(&defLock);
    buttonPress = true;
    spin_unlock(&defLock);
    
    old_jiffie = jiffies;
    
    printk(KERN_INFO "Led state is: [%d] \n", gpio_get_value(Led));
    printk(KERN_INFO "Button state is: [%d] \n", gpio_get_value(Button));
    		
    counter++;
    return (irq_handler_t) IRQ_HANDLED;
}

/**
 * @brief The device open function that is called each time the device is opened
 *  This will only increment the numberOpens counter in this case.
 */
static int dev_open(struct inode *inodep, struct file *filep){
    printk(KERN_INFO "tempchar: Device has been opened\n");
    return 0;
}

/** @brief This function is called whenever device is being read from user space i.e. data is
 *  being sent from the device to the user. In this case is uses the copy_to_user() function to
 *  send the buffer string to the user and captures any errors.
 */
static ssize_t dev_read(struct file *filep, char *buffer, size_t len, loff_t *offset) {
   
    printk(KERN_INFO "reading now!!!\n");
    unsigned char sendByte = 0;
    unsigned long flags;
    int error_count;

    if (buttonPress) {
       sendByte = 1;
       spin_lock_irqsave(&defLock, flags);
       buttonPress = false;
       spin_unlock_irqrestore(&defLock, flags);
       printk(KERN_INFO "button has been pressed1\n");
    }
    copy_to_user(buffer, &sendByte, 1);

    if (error_count==0){            // if true then have success
      printk(KERN_INFO "TempChar: Sent %d characters to the user\n", 1);
      return (1);  // clear the position to the start and return 0
    }
    else {
      printk(KERN_INFO "TempChar: Failed to send %d characters to the user\n", error_count);
      return -EFAULT;              // Failed -- return a bad address message (i.e. -14)
    }
    return 1;
}

/** @brief This function is called whenever the device is being written to from user space i.e.
 *  data is sent to the device from the user. The data is copied to the message[] array in this
 *  LKM using the sprintf() function along with the length of the string.
 */
static ssize_t dev_write(struct file *filep, const char *buffer, size_t len, loff_t *offset){
    return 0;
}

/** @brief The device release function that is called whenever the device is closed/released by
 *  the userspace program
 */
static int dev_release(struct inode *inodep, struct file *filep){
    printk(KERN_INFO "TempChar: Device successfully closed\n");
    return 0;
}

/**
 * @brief This function is called when the module is loaded into the kernel 
 */
static int __init Module_Init(void) {
    pr_info("%s\n", __func__);
    printk("irq test");
    printk("qpio_irq: Loading module...\n");

    /*  Setup GPIO  */
    if(!gpio_is_valid(Button)){
        printk(KERN_INFO "Invalid GPIO\n");
        return -ENODEV;
    }

    if(gpio_request(Button, "rpi-gpio-17")) {
        printk("Error!\nCan not request GPIO17!\n");
        gpio_free(Button);
        return -1;
    }

    /*  Set GPIO 17 direction   */
    if(gpio_direction_input(Button)) {
        printk("Error!\nCannot set GPIO 17 to input!\n");
        gpio_free(Button);
        return -1;
    }

    gpio_export(Button, false);

    if(!gpio_is_valid(Led)){
        printk(KERN_INFO "Invalid GPIO\n");
        return -ENODEV;
    }

    if(gpio_request(Led, "rpi-gpio-16")) {
        printk("Error!\nCan not request GPIO16!\n");
        gpio_free(Led);
        return -1;
    }

    if(gpio_direction_output(Led, 1)) {
        printk("Error!\nCan not set GPIO 16\n");
        gpio_free(Led);
        return -1;
    }

    /* Make it appear in /sys/class/gpio/gpio16 for echo 0 > value */
    gpio_export(Led, false);

    /* Setup the interrupt  */ 
    irq_number = gpio_to_irq(Button);
    if(request_irq(irq_number, 
            (irq_handler_t) gpio_irq_handler,   /* pointer to IRQ handler method */
            IRQF_TRIGGER_RISING, 
            "my_gpio_irq",  /* See this string from user console to identify: cat /proc/interrupts */
            NULL) != 0) {

        printk ("Error!\nCannot request interrupt number: %d\n", irq_number);
        gpio_free(Button);
        return -1;
    }

    majorNumber = register_chrdev(0, DEVICE_NAME, &fops);

    if (majorNumber<0){
      printk(KERN_ALERT "TempChar failed to register a major number\n");
      return majorNumber;
    }
    printk(KERN_INFO "TempChar: registered correctly with major number %d\n", majorNumber);

    // Register the device class
    tempcharClass = class_create(THIS_MODULE, CLASS_NAME);
    if (IS_ERR(tempcharClass)){                // Check for error and clean up if there is
       unregister_chrdev(majorNumber, DEVICE_NAME);
       printk(KERN_ALERT "Failed to register device class\n");
       return PTR_ERR(tempcharClass);          // Correct way to return an error on a pointer
    }
    printk(KERN_INFO "TempChar: device class registered correctly\n");

    // Register the device driver
    tempcharDevice = device_create(tempcharClass, NULL, MKDEV(majorNumber, 0), NULL, DEVICE_NAME);
    if (IS_ERR(tempcharDevice)){               // Clean up if there is an error
       class_destroy(tempcharClass);           // Repeated code but the alternative is goto statements
       unregister_chrdev(majorNumber, DEVICE_NAME);
       printk(KERN_ALERT "Failed to create the device\n");
       return PTR_ERR(tempcharDevice);
    }
    printk(KERN_INFO "TempChar: device class created correctly\n"); // Made it! device was initialized

    printk("Done!\n");
    printk("GPIO 17 is mapped to IRQ Number: %d\n", irq_number);
    return 0;
}

/**
 * @brief This function is called when the module is removed from the kernel
 */
static void __exit Module_Exit(void) {
    printk ("gpio_irq: Unloading module...\n");
    gpio_set_value(Led, 0);
    gpio_unexport(Led);
    free_irq(irq_number, NULL);
    gpio_free(Button);
    gpio_free(Led);
    printk("gpio_irq: Module Unloaded\n");
}

module_init(Module_Init);
module_exit(Module_Exit);
