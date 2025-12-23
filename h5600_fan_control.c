/*
 * ASUS H5600 Fan Control Module - Prototype
 *
 * This attempts to control fans on ASUS ProArt H5600 by directly
 * communicating with the ASUS WMI interface.
 *
 * Based on reverse-engineering of G-Helper and asus-wmi kernel driver.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/acpi.h>
#include <linux/platform_device.h>

#define ASUS_WMI_MGMT_GUID "97845ED0-4E6D-11DE-8A39-0800200C9A66"

/* Method IDs */
#define ASUS_WMI_METHODID_DSTS  0x53545344  /* Device Status */
#define ASUS_WMI_METHODID_DEVS  0x53564544  /* Device Set */
#define ASUS_WMI_METHODID_INIT  0x54494E49  /* Init */

/* Device IDs */
#define ASUS_WMI_DEVID_THERMAL_POLICY_VIVO  0x00110019
#define ASUS_WMI_DEVID_CPU_FAN_CTRL         0x00110013
#define ASUS_WMI_DEVID_GPU_FAN_CTRL         0x00110014
#define ASUS_WMI_DEVID_CPU_FAN_DIRECT       0x00110022
#define ASUS_WMI_DEVID_GPU_FAN_DIRECT       0x00110023

static int asus_wmi_evaluate_method(u32 method_id, u32 arg0, u32 arg1, u32 *retval)
{
    struct acpi_buffer input = { sizeof(u32) * 2, NULL };
    struct acpi_buffer output = { ACPI_ALLOCATE_BUFFER, NULL };
    union acpi_object *obj;
    u32 args[2] = { arg0, arg1 };
    acpi_status status;
    int ret = 0;

    input.pointer = args;

    status = wmi_evaluate_method(ASUS_WMI_MGMT_GUID, 0, method_id, &input, &output);
    if (ACPI_FAILURE(status)) {
        pr_err("h5600_fan: WMI method call failed: %s\n", acpi_format_exception(status));
        return -EIO;
    }

    obj = output.pointer;
    if (obj && obj->type == ACPI_TYPE_INTEGER) {
        if (retval)
            *retval = obj->integer.value;
    } else {
        ret = -ENODATA;
    }

    kfree(obj);
    return ret;
}

static int set_thermal_policy(int mode)
{
    u32 retval;
    int ret;

    /* Mode: 0=balanced, 1=turbo, 2=silent */
    ret = asus_wmi_evaluate_method(ASUS_WMI_METHODID_DEVS,
                                    ASUS_WMI_DEVID_THERMAL_POLICY_VIVO,
                                    mode, &retval);
    if (ret)
        return ret;

    pr_info("h5600_fan: Set thermal policy to %d, result: 0x%x\n", mode, retval);
    return (retval == 1) ? 0 : -EINVAL;
}

static int get_fan_speed(int fan, u32 *speed)
{
    u32 devid = (fan == 0) ? ASUS_WMI_DEVID_CPU_FAN_CTRL : ASUS_WMI_DEVID_GPU_FAN_CTRL;
    return asus_wmi_evaluate_method(ASUS_WMI_METHODID_DSTS, devid, 0, speed);
}

/* Try direct fan control - this may not work on all models */
static int set_fan_speed_direct(int fan, int percent)
{
    u32 devid = (fan == 0) ? ASUS_WMI_DEVID_CPU_FAN_DIRECT : ASUS_WMI_DEVID_GPU_FAN_DIRECT;
    u32 retval;
    int ret;

    ret = asus_wmi_evaluate_method(ASUS_WMI_METHODID_DEVS, devid, percent, &retval);
    if (ret)
        return ret;

    pr_info("h5600_fan: Set fan %d to %d%%, result: 0x%x\n", fan, percent, retval);
    return (retval == 1) ? 0 : -EOPNOTSUPP;
}

/* Sysfs interface */
static ssize_t thermal_policy_store(struct device *dev, struct device_attribute *attr,
                                     const char *buf, size_t count)
{
    int mode;
    if (kstrtoint(buf, 10, &mode) || mode < 0 || mode > 2)
        return -EINVAL;

    if (set_thermal_policy(mode))
        return -EIO;

    return count;
}

static ssize_t cpu_fan_show(struct device *dev, struct device_attribute *attr, char *buf)
{
    u32 speed;
    if (get_fan_speed(0, &speed))
        return -EIO;
    return sprintf(buf, "%u\n", speed & 0xFFFF);
}

static DEVICE_ATTR_WO(thermal_policy);
static DEVICE_ATTR_RO(cpu_fan);

static struct attribute *h5600_attrs[] = {
    &dev_attr_thermal_policy.attr,
    &dev_attr_cpu_fan.attr,
    NULL
};

static struct attribute_group h5600_attr_group = {
    .attrs = h5600_attrs,
};

static struct platform_device *h5600_pdev;

static int __init h5600_fan_init(void)
{
    int ret;
    u32 val;

    if (!wmi_has_guid(ASUS_WMI_MGMT_GUID)) {
        pr_err("h5600_fan: ASUS WMI GUID not found\n");
        return -ENODEV;
    }

    /* Test if thermal policy is supported */
    ret = asus_wmi_evaluate_method(ASUS_WMI_METHODID_DSTS,
                                    ASUS_WMI_DEVID_THERMAL_POLICY_VIVO,
                                    0, &val);
    if (ret) {
        pr_err("h5600_fan: Thermal policy VIVO not supported\n");
        return -ENODEV;
    }
    pr_info("h5600_fan: Current thermal policy: 0x%x\n", val);

    /* Create platform device */
    h5600_pdev = platform_device_register_simple("h5600_fan", -1, NULL, 0);
    if (IS_ERR(h5600_pdev))
        return PTR_ERR(h5600_pdev);

    ret = sysfs_create_group(&h5600_pdev->dev.kobj, &h5600_attr_group);
    if (ret) {
        platform_device_unregister(h5600_pdev);
        return ret;
    }

    pr_info("h5600_fan: Module loaded. Use /sys/devices/platform/h5600_fan/\n");
    return 0;
}

static void __exit h5600_fan_exit(void)
{
    sysfs_remove_group(&h5600_pdev->dev.kobj, &h5600_attr_group);
    platform_device_unregister(h5600_pdev);
    pr_info("h5600_fan: Module unloaded\n");
}

module_init(h5600_fan_init);
module_exit(h5600_fan_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("H5600 Fan Control Project");
MODULE_DESCRIPTION("Fan control for ASUS ProArt H5600");
