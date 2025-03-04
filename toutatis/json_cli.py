import argparse
import contextlib
from html import parser
import json
import os
import sys

from toutatis.core import getUserId, getInfo, advanced_lookup

import phonenumbers
from phonenumbers.phonenumberutil import (
    region_code_for_country_code,
    region_code_for_number,
)
import pycountry


def output_destination(value):
    """
    If the user passes 'stdout' or 'stderr', return the corresponding stream.
    Otherwise, treat the value as a filename and attempt to open it for writing.
    """
    if value.lower() == 'stdout':
        return sys.stdout
    elif value.lower() == 'stderr':
        return sys.stderr
    else:
        try:
            # Open the file for writing.
            return open(value, 'w')
        except Exception as e:
            raise argparse.ArgumentTypeError(f"Cannot open file '{value}' for writing: {e}")


def main():
    parser = argparse.ArgumentParser(description="Toutatis is a tool that allows you to extract information from instagrams accounts such as e-mails, phone numbers and more ")
    parser.add_argument('-s', '--sessionid', help="Instagram session ID", required=True)
    parser.add_argument(
        '-o', '--output',
        type=output_destination,
        default=sys.stdout,
        help="output result destination: specify a filename, 'stdout' for standard output, or 'stderr' for standard error."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--username', help="One username")
    group.add_argument('-i', '--id', help="User ID")
    args = parser.parse_args()
    
    session_id = args.sessionid
    search_type = "id" if args.id else "username"
    search = args.id or args.username
    output = args.output
    
    with contextlib.ExitStack() as stack:
        if output not in (sys.stdout, sys.stderr):
            stack.callback(output.close)
        
        infos = getInfo(search, session_id, searchType=search_type)
        if not infos.get("user"):
            print(infos["error"], file=sys.stderr)
            sys.exit(1)
        
        infos = infos["user"]
        
        results = {
            "target": infos["username"],
            "userID": infos["userID"],
            "full_name": infos["full_name"],
            "verified": infos['is_verified'],
            "is_business": infos["is_business"],
            "is_private": infos["is_private"],
            "follower_count": infos["follower_count"],
            "following_count": infos["following_count"],
            "media_count": infos["media_count"],
            "external_url": infos["external_url"],
            "total_igtv_videos": infos["total_igtv_videos"],
            "biography": (f"""\n{" " * 25}""").join(infos["biography"].split("\n")),
            "is_whatsapp_linked": infos["is_whatsapp_linked"],
            "is_memorialized": infos["is_memorialized"],
            "is_new_to_instagram": infos["is_new_to_instagram"],
            "public_email": infos.get("public_email"),
            "public_phone_number": infos.get("public_phone_number"),
            "public_phone_country_code": infos.get("public_phone_country_code"),
        }
        
        if results["public_phone_number"]:
            phonenr = f"+{results['public_phone_country_code']} {results['public_phone_number']}"
            try:
                pn = phonenumbers.parse(phonenr)
                countrycode = region_code_for_country_code(pn.country_code)
                country = pycountry.countries.get(alpha_2=countrycode)
                phonenr = f"{phonenr} ({country.name})"
            except Exception as e:
                pass
            results["public_phone_number"] = phonenr
            
        other_infos = advanced_lookup(infos["username"])
        if other_infos["error"] == "rate limit":
            print("Rate limit reached, please try again later.", file=sys.stderr)
        elif "message" in other_infos["user"]:
            if other_infos["user"]["message"] == "No users found":
                # print("The lookup did not work on this account", file=sys.stderr)
                pass
            else:
                results["message"] = other_infos["user"]["message"]
        else:
            if "obfuscated_email" in other_infos["user"].keys():
                if other_infos["user"]["obfuscated_email"]:
                    results["obfuscated_email"] = other_infos["user"]["obfuscated_email"]
                else:
                    # print("No obfuscated email found", file=sys.stderr)
                    pass
            
            if "obfuscated_phone" in other_infos["user"].keys():
                if str(other_infos["user"]["obfuscated_phone"]):
                    results["obfuscated_phone"] = other_infos["user"]["obfuscated_phone"]
                else:
                    # print("No obfuscated phone found", file=sys.stderr)
                    pass
                
        results["profile_pic_url"] = infos["hd_profile_pic_url_info"]["url"]
        
        json.dump(results, args.output, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main()
