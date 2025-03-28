import os
import fnmatch
import re

def get_files_by_extension(directory, extension):
    """
    Returns a list of files matching the extension in the directory..
    Args:
        directory (str): Directory to search for files.
        extension (str): file extension to search for.
    """
    return [f for f in os.listdir(directory) if fnmatch.fnmatch(f, f"*{extension}")]

def find_and_read_chat_file(file_names: list) -> list:
    """
    Peruses through a list of filenames, selects and read the one matching whatsapp
    chat naming conventions.
    Args:
        file_names (list): All the text files in the chat-details directory.
    Returns:
        file_content (list): The chat content of the text file with each message as a str.
    """
    file = None
    for a_file in file_names:
        if a_file[:8] == "WhatsApp":
            file = a_file
            break

    if len(file_names) < 1 or not file:
        raise FileNotFoundError
    with open(f"static/chat-details/{file}", mode="r", encoding="utf-8") as txtfile:
        file_content = txtfile.readlines()
    return file_content
print('WhatsApp Chat'[:8])

def organize_msgs(msg_list: list) -> list:
    """
    Processes and merges messages that were unintentionally split
    across multiple lines due to newlines.
    Args:
        msg_list (list of str): A list of lines from the WhatsApp chat file.
    Returns:
        msg_list (list of str): A cleaned-up list where multiline messages are correctly
                     merged into single entries.
    """
    stopped = 0
    repeat = False
    msg_list = msg_list.copy()
    while True:
        for i in range(len(msg_list)):
            if stopped == len(msg_list):
                repeat = False
                continue
            if i < stopped:
                continue
            if not msg_list[i][0].isdigit() or msg_list[i][:8].count("/") != 2:
                if i == 0:
                    print("raise error 5-something")
                added = msg_list[i-1] + " " + msg_list[i]
                msg_list[i-1] = added
                msg_list.pop(i)
                stopped = i
                repeat = True
                break
            repeat = False
        if repeat:
            continue
        break
    return msg_list

def extract_contact(filename: str):
    try:
        with open(f"static/chat-details/{filename}", "r", encoding="utf-8") as file:
            vcf_content = file.read()
    except FileNotFoundError:
        return "|"

    fn_match = re.search(r"FN:(.+)", vcf_content)

    tel_match = re.search(r"TEL;type=.*?:\+?([\d\s]+)", vcf_content)

    if tel_match:
        phone_number = tel_match.group(1).replace(" ", "").strip("\n")
        phone_number = "0" + phone_number[3:]
        return f"{fn_match.group(1)}|{phone_number}"
    else:
        return "|"

def caution_split(text: str, delimiter: str, n: int) -> list:
    """
    Splits text into at most n parts using delimiter.
    If the split results in more than n parts, all parts after the first n-1 are joined back together using delimiter
    as a separator.
    Args:
        text (str): The string to be split.
        delimiter (str): The text separator.
        n (int): Maximum split amount
    Returns:
        split_text (list of str): A list containing up to n parts of the text after splitting.
    """
    split_text = text.split(delimiter)
    if len(split_text) > n:
        second_part = ""
        for j in range(len(split_text)):
            if j == 0:
                continue
            second_part += split_text[j] + delimiter
        split_text = [split_text[0], second_part]
    return split_text

def detect_encrypted_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            signature = f.read(8).hex().upper()
    except OSError:
        return None

    # Common file signatures
    file_signatures = {
        "25504446": ".pdf",  # PDF
        # "504B0304": ".docx",  # ZIP-based formats (DOCX, XLSX, PPTX)
        # "504B0708": ".zip",  # ZIP file
        # "D0CF11E0": ".doc",  # Older DOC format
    }

    for sig, ext in file_signatures.items():
        if signature.startswith(sig):
            new_name = file_path.replace(". ", "") + ext
            print(new_name)
            os.rename(file_path, new_name)
            return ext
    return None

def parse_chat(messages: list) -> list:
    """
    Parses a list of WhatsApp chat messages and extracts relevant details such as date, time, sender, message body,
    and message type.
    Args:
        messages (list of str): A list of WhatsApp chat messages, where each message follows the standard
                                format of a WhatsApp export.

    Returns:
        parsed_chat (list of dict): A list of dictionaries where each dictionary represents a structured
                                    chat message with the following keys:
            - "date" (str): The date of the message.
            - "time" (str): The time the message was sent.
            - "name" (str, optional): The sender's name (excluded for "info" messages).
            - "body" (str): The actual message content.
            - "type" (str): The type of message, which can be one of:
                - "text" (regular message)
                - "sticker" (WhatsApp sticker)
                - "image" (image file)
                - "audio" (voice note)
                - "video" (video file)
                - "contact" (shared contact)
                - "info" (system-generated messages)
            - "edited" (bool): Whether the message was edited (True if it contains "<This message was edited>").
    """
    parsed_chat = []
    for i in messages:
        temp_list = caution_split(i, " - ", 2)
        print(temp_list)
        date, time = temp_list[0].split(", ")
        # try:
        #     date, time = temp_list[0].split(", ")
        # except ValueError:
        #     print(ValueError)
        #     print(i)
        #     print(len(i), len(temp_list))
        #     print(temp_list)
        if ":" not in temp_list[1]:
            a_chat = {"date": date, "time": time, "body": temp_list[1], "type": "info"}
            parsed_chat.append(a_chat)
            continue
        name, msg_body = caution_split(temp_list[1], ": ", 2)
        if "(file attached)" not in msg_body:
            msg_type = "text"
        elif msg_body[:3] == "STK":
            msg_type = "sticker"
        elif msg_body[:3] == "IMG":
            msg_type = "image"
            msg_body = msg_body.replace("(file attached)\n", "|")
        elif msg_body[:3] == "PTT" or msg_body[:3] == "AUD":
            print("ghy music", msg_body)
            msg_type = "audio"
        elif msg_body[:3] == "VID":
            msg_type = "video"
        elif ".vcf" in msg_body:
            msg_type = "contact"
            msg_body = extract_contact(msg_body.split(".vcf")[0] + ".vcf")
        elif detect_encrypted_pdf(f"static/chat-details/{msg_body.replace("(file attached)\n", "")}"):
            msg_type = "pdf"
            print("pdf found")
            msg_body = msg_body.replace("(file attached)\n", "|")
            if "DOC" in msg_body:
                msg_body = msg_body.replace(" |", "pdf")
            print(msg_body)
        elif re.search(r"\b[\w\s()-]+\.[a-zA-Z0-9]{2,5}\b", msg_body) or "DOC" in msg_body:
            print("ghy document", msg_body)
            msg_body = msg_body.replace("(file attached)\n", "|")
        else:
            msg_type = "text"

        if msg_type != "text":
            msg_body = msg_body.replace("(file attached)\n", "|").strip(" ")
        if "<This message was edited>" in msg_body:
            edited = True
            msg_body = msg_body.removesuffix("<This message was edited>\n")
        else:
            edited = False
        if "Media omitted" in msg_body:
            msg_body = msg_body.replace("<", "")
        #"contact, video, vn/audio, image, sticker, text"
        a_chat = {"date": date, "time": time, "name": name, "body": msg_body, "type": msg_type, "edited": edited}
        parsed_chat.append(a_chat)
    return parsed_chat

def get_names(parsed_chat: list)-> list:
    """
    Extracts all unique names from a parsed WhatsApp chat dictionary.
    Args:
        parsed_chat (list of dict): A list of chat dictionaries containing keys like "name".

    Returns:
        list: A sorted list of unique names found in the chat.
    """
    return sorted({chat["name"] for chat in parsed_chat if "name" in chat})

from pprint import pprint
files = get_files_by_extension("static/chat-details", ".txt")
txt_content = find_and_read_chat_file(files)
from pprint import pprint
print(len(txt_content))
new = organize_msgs(txt_content)
print(len(new))
# for m in new:
#     print("--$--")
#     print(m)
# pprint(new)
chat = parse_chat(new)
pprint(chat)
print("oioi")
print(get_names(chat))


import shutil
#
# def delete_directory(dir_path):
#     """
#     Deletes a directory and all its contents.
#
#     Args:
#         dir_path (str): The path to the directory.
#
#     Returns:
#         None
#     """
#     try:
#         shutil.rmtree(dir_path)
#         print(f"Deleted directory and its contents: {dir_path}")
#     except FileNotFoundError:
#         print(f"Directory not found: {dir_path}")
#     except Exception as e:
#         print(f"Error: {e}")
#
# delete_directory("./static/chat-details/")

# a = {0: "Asked her. She Took me to director's office. He's not around so she "
#          'said when he comes back.\n',
#      1: 'There are 2 roles I mentioned to director.\n'
#              ' ML tutor and intern, which do you think I should mention to ayo, '
#              'both? I would prefer the ML tutor own\n',
#      }
#
# print("qwer.vcf"[:-4])
# import re
#
#
# print(extract_contact("Ayo Nithub.vcf"))