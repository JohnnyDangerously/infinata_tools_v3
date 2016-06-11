import time
import datetime
import sys
import getpass
import re
import os
import random
from dynect.DynectDNS import DynectRest
from pprint import PrettyPrinter

# TODO Break ouf of two additional loops for the DR verification block
# TODO add " to the are you sure present the option selected to question"
# TODO remove 300 from the log entry
# TODO where it says saving back up file, add file name and path

zone_list = []
current_time = time.strftime("%d%m%Y-%H%M%S")

# parameter / file name configuration
args = sys.argv
help_list = ["/?", "?", "help", "-h", "-he4lp"]
print(args)

# Login to API
api = DynectRest()
print("Log in DYN API")

pargs = {'customer_name': 'Infinata',
        'user_name': input('Enter your Dynect username: '),
        'password': getpass.getpass(prompt='Password:')
         }

print("** Logging in...")
response = api.execute('/REST/Session/', 'POST', pargs)

if response['status'] != 'success':
    pretty = PrettyPrinter()
    msg = "** Login to API failed: %s" % pretty.pformat(response)
    sys.exit(msg)

print("** Login successful.")
print(args)

if args in help_list:
    print("*** NAME: dyndns tool \n"
          "DESCRIPTION: " + "utilizes flat file to make bulk changes to dyndns domain records"
          "BASIC USEAGE: python dyndns.py {optional file path to backup or custom change file")
    exit(0)
elif len(args) == 1:
    while True:
        print(" Change DNS records: \n"
              "    1  Change all 'A' records to maintenance\n"
              "    2  Change all 'A' records to production\n"
              "    3  Change all 'A' records to DR\n"
              "    4  Restore changes since last run\n"
              "    5  Exit \n")
        answer = input("Change DNS A records: \n")
        if answer == "1":
            while True:
                res = input("are you sure? (y / n)")
                if res == "y":
                    dns_change_file = "PRODchanges.txt"
                    break
                elif res == "n":
                    break
                else:
                    continue
            break
        elif answer == "2":
            while True:
                res = input("are you sure? (y / n)")
                if res == "y":
                    dns_change_file = "MAINTchanges.txt"
                    break
                elif res == "n":
                    break
                else:
                    continue
            break
        elif answer == "3":
            dns_change_file = "DRchanges.txt"
            while True:
                res = input("are you sure? (y / n)")
                if res == "y":
                    while True:
                        res = input("!!ARE YOU ABSOLUTELY SURE THIS WILL REDIRECT ALL TRAFFIC TO DR!! (y / n)")
                        if res == "y":
                            dns_change_file = "MAINTchanges.txt"
                            break
                        elif res == "n":
                            break
                        else:
                            continue
                elif res == "n":
                    break
                else:
                    continue
        elif answer == "4":
            print("Pick which backup file\n")
            fn_dict = {}
            fn_list = []
            patty = re.compile("\d+-\d+_dnschangesBACKUP\.txt")
            for file in os.listdir('.'):
                search_results = patty.search(file)
                if search_results:
                    fn_list.append(file)
            for each_item in fn_list:
                fn_dict[each_item.split('_')[0]] = each_item
            sorted_fn_list = sorted(fn_dict, key=lambda x: datetime.datetime.strptime(x, '%d%m%Y-%H%M%S'))
            n = 0
            for fn_item in sorted_fn_list[:4]:
                n += 1
                print(str(n) + ")" + " " + fn_dict[fn_item])
                with open(fn_dict[fn_item], 'r') as fin:
                    print(fin.read())
            while True:
                answer = input("Load which backup file?: ")
                if answer == "1":
                    dns_change_file = fn_dict[sorted_fn_list[0]]
                    break
                elif answer == "2":
                    dns_change_file = fn_dict[sorted_fn_list[1]]
                    break
                elif answer == "3":
                    dns_change_file = fn_dict[sorted_fn_list[2]]
                    break
                elif answer == "4":
                    dns_change_file = fn_dict[sorted_fn_list[3]]
                    break
                elif answer == "5":
                    dns_change_file = fn_dict[sorted_fn_list[4]]
                    break
                else:
                    print("please select only 1-5\n")
                    continue
            break
        elif answer == "5":
            exit(0)
        else:
            print(" please type 1-4 ")
            continue
elif len(args) == 2:
    dns_change_file = args[1]
elif len(args) > 2:
    print("filename error or too many arguments, please only include a file path with no spaces")
    exit(0)


try:  # preconditions can create race conditions use try: except
    with open(dns_change_file, 'r') as f:
        read_data = f.readlines()
except FileNotFoundError:
    print("** dnschanges.txt file not found in script directory or no file path given\n")
    print("** creating example dnschange.txt file in current directory")
    print("** please modify and rerun the script")
    with open(dns_change_file, 'w') as f:
        f.write("## 1) Please uncomment TTL and give TTL the desired value\n"
                "## 2) Please append changes as <domain> <Ipaddress>\n"
                "## api.cheerios.com 76.33.132.22 (example)\n"
                "#TTL=300\n"
                "\n")
    exit(0)
    print("please modify dnschanges.txt and try again")


# dns_change_file = args[1]
domain_list = {}
for item in read_data:
    if re.match(r'^\s*$', item):
        continue
    if "#" in item:
        continue
    if "TTL" in item:
        ttl = item.split('=')[1].strip("\n")
        continue
    try:
        domain_list[item.split()[0]] = [item.split()[1], ttl]
    except (NameError, IndexError) as e:
        if 'ttl' in str(e):
            print("** TTL is missing or not correctly defined")
            exit(1)
        else:
            print("error information: " + str(e))
            print("** Missing either TTL or IP for a change request: ")
            print(item)
            exit(1)


# extract and store Zones from domain_list dictionary
for zone1 in domain_list.keys():
    zone_item1 = '.'.join(zone1.split('.')[-2:])
    zone_list.append(zone_item1)

# print current A records
before_dict = {}
print("comparing current records to requested changes....")
print("\n")
for fqdn in domain_list.keys():
    zone = '.'.join(fqdn.split('.')[-2:])
    action1 = api.execute("REST/ARecord/" + zone + "/" + fqdn, 'GET')
    if action1['status'] == "failure":
        print("failed")
        if action1['msgs'][0]['INFO'] == "zone: No such zone":
            print("Wrong zone detected, please check change file for domain name errors")
            exit(0)
        elif action1['msgs'][0]['INFO'] == "node: Not in zone":
            print("Wrong sub-domain detected, please check change file for domain name errors")
            exit(0)
        else:
            print(action1['msgs'][0]['INFO'])
    action2 = api.execute(action1["data"][0], 'GET')
    before_dict[action2["data"]["fqdn"]] = [action2["data"]["rdata"]["address"], action2["data"]["ttl"]]

# take a dictionary of changes and apply them
check_list = []
for domain_name in domain_list.keys():
    zone = '.'.join(domain_name.split('.')[-2:])  # Extract zone from FQDN
    response = api.execute("REST/ARecord/" + zone + "/" + domain_name + "/", 'GET')
    record_change = {'rdata': {'address': domain_list[domain_name][0]}, 'ttl': domain_list[domain_name][1]}
    change_response = api.execute(response["data"][0], 'PUT', record_change)
    check_list.append(change_response['msgs'][0]['INFO'])
    if change_response['msgs'][0]['INFO'] == 'update: No changes specified':
        print("no change to be made to " + domain_name)

# add in break out if no changes are to be made
#
# for response_msg in check_list:
#     if response_msg != 'update: No changes specified':
#         print("no changes to be made please choose or modify domains to be changed.")
#         exit(0)

# compare changes to A records
print("changes to be made:")
backup_list = {}
for zone_check in set(zone_list):
    response1 = api.execute("REST/ZoneChanges/" + zone_check, 'GET')
    if response1["data"]:  # make sure list is not empty
        for item_fqdn in response1["data"]:
            if item_fqdn["fqdn"] in before_dict.keys():
                backup_list[item_fqdn["fqdn"]] = [before_dict[item_fqdn["fqdn"]]]
                print(item_fqdn["fqdn"] + " " + str(before_dict[str(item_fqdn["fqdn"])]) +
                      "  changing to  " + str(item_fqdn["rdata"]["rdata_a"]["address"]), str(item_fqdn["ttl"]))


# publish the zone changes to Dynect
print("\n")
while True:
    answer = input("Do you want to publish the above changes? type (y or n):")
    if answer.lower() == "y":
        print("creating backup file...")
        file_time = current_time + "_" + "dnschangesBACKUP.txt"
        with open(file_time, 'w') as f:
            f.write("TTL=" + str(before_dict[random.choice(list(before_dict.keys()))][1]) + "\n")
        with open("dns.log", 'a') as logf:
            logf.write("\n")
            logf.write("change committed on " + current_time + "\n")
            logf.write("TTL=" + str(before_dict[random.choice(list(before_dict.keys()))][1]) + "\n")
        for backup_domain in backup_list.keys():
            with open(file_time, 'a') as f:
                f.write(str(backup_domain) + " " + str(before_dict[backup_domain][0]) + "\n")
            with open("dns.log", 'a') as logf:
                logf.write(str(backup_domain) + " " + str(domain_list[backup_domain][0]) + " " + str(before_dict[backup_domain][1]) + "\n")
        for zone_item in set(zone_list):
            arguments = {'publish': 'true'}
            URI = '/Zone/' + zone_item
            zone_response = api.execute(URI, 'PUT', arguments)
            print("saving changes to zone: " + zone_item + ' ... ' + zone_response["status"])
        break
    elif answer.lower() == "n":
        for zone_check in set(zone_list):
            response1 = api.execute("REST/ZoneChanges/" + zone_check, 'DELETE')
        break
    else:
        print("\n")
        print("please enter 'y' or 'n' ")
        continue

# logging out of the API
print("Logging out")
api.execute('/REST/Session/', 'DELETE')
exit(0)
