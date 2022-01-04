#include <linux/module.h>
#include <linux/init.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>

/* Meta Information */
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Tom Gardner");
MODULE_DESCRIPTION("An LKM for a gpio interrupt that lights up an LED");
MODULE_VERSION("0.1");

static unsigned int Led = 16;
static unsigned int Button = 17;
static unsigned int counter = 0;
static bool state = 0;
/* variable contains pin number interrupt controller to which GPIO 17 is mapped to */
static unsigned int irq_number;

/**
 * @brief Interrupt service routine is called when the interrupt is triggered
 * 
 */
static irq_handler_t gpio_irq_handler(unsigned int irq, void *dev_id, struct pt_regs *regs) {
    printk("gpio_irq: Interrupt was triggered and ISR was called!\n");

    state = !State; /* Toggle LED */
    gpio_set_value(Button, Led);
    printk(KERN_INFO "Led state is: [%d] ", gpio_get_value(Led))
    printk(KERN_INFO "Button state is: [%d] ", gpio_get_value(Button))

    counter++;
    return (irq_handler_t) IRQ_HANDLED;
}

/**
 * @brief This function is called when the module is loaded into the kernel 
 * 
 */
static int __init module_init(void) {
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
     
    if(gpio_set_debounce(Button, 500)) {
        printk("Error!\nCannot set debounce")
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

    printk("Done!\n");
    printk("GPIO 17 is mapped to IRQ Number: %d\n", irq_number);
    return 0;
}

/**
 * @brief This function is called when the module is removed from the kernel
 * 
 */
static void __exit module_exit(void) {
    printk ("gpio_irq: Unloading module...");
    gpio_set_value(Led, 0);
    gpio_unexport(Led);
    free_irq(irq_number, NULL);
    gpio_free(Button);
    gpio_free(Led);
    printk("gpio_irq: Module Unloaded");
}

module_init(module_init)
module_exit(module_exit)
