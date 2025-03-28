from flask import Flask, abort, render_template, redirect, url_for, flash, request
from zipfile import ZipFile
import os
import re
import fnmatch
from datetime import datetime
import shutil
import json

class ChatManager:
    """
    Manages chat data and user information.

    Attributes:
        chat (list or None): Stores the chat messages.
        username (str or None): Stores the username of the chat participant.
    """
    def __init__(self):
        """
        Initializes the ChatManager with no chat data or username set.
        """
        self.chat = None
        self.username = None

    def set_chat(self, chat: list):
        """
        Sets the chat messages.
        Args:
            chat (list): A list of chat messages.
        """
        self.chat = chat

    def set_name(self, name: str):
        """
        Sets the username of the chat participant.
        Args:
            name (str): The username to be set.
        """
        self.username = name


class TamperedFileError(Exception):
    """
    Custom exception for handling improperly structured files.
    Raised when a file does not follow the expected format.
    """

    def __init__(self, message="What kinda file is this fam?"):
        """
        Initializes the exception with a default or custom error message.
        Args:
            message (str, optional): The error message to display. Defaults to a casual phrasing.
        """
        super().__init__(message)


chat_manager = ChatManager()


def delete_directory(dir_path):
    """
    Deletes a directory and all its contents.
    Args:
        dir_path (str): The path to the directory.
    Returns:
        None
    """
    try:
        shutil.rmtree(dir_path)
        print(f"Deleted directory and its contents: {dir_path}")
    except FileNotFoundError:
        print(f"Directory not found: {dir_path}")
    except Exception as e:
        print(f"Error: {e}")


def extract_zipfile(file):
    """
    Extracts the contents of a ZIP file into the 'static/chat-details' directory.
    Args:
        file (str or file-like object): The ZIP file to be extracted.
    Returns:
        None
    """
    # Clear files left in the chat details directory.
    delete_directory("static/chat-details")
    # Extract zipfile
    with ZipFile(file, 'r') as zObject:
        # Extracting all the members of the zip
        # into a specific location.
        zObject.extractall(
            path="static/chat-details")


def get_files_by_extension(directory, extension):
    """
    Returns a list of files matching the extension in the directory..
    Args:
        directory (str): Directory to search for files.
        extension (str): file extension to search for.
    """
    return [f for f in os.listdir(directory) if fnmatch.fnmatch(f, f"*{extension}")]


def detect_encrypted_pdf(file_path):
    """
    Detects if a file is a PDF by checking its signature and renames it accordingly.
    Args:
        file_path (str): The path to the file being checked.
    Returns:
        str or None: The detected file extension (e.g., ".pdf") if matched, otherwise None.
    """
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
            os.rename(file_path, new_name)
            return ext
    return None


def get_names(parsed_chat: list) -> list:
    """
    Extracts all unique names from a parsed WhatsApp chat dictionary.
    Args:
        parsed_chat (list of dict): A list of chat dictionaries containing keys like "name".
    Returns:
        list: A sorted list of unique names found in the chat.
    """
    return sorted({chat["name"] for chat in parsed_chat if "name" in chat})


def extract_contact(filename: str):
    """
    Extracts the contact name and phone number from a VCF (vCard) file.
    Args:
        filename (str): The name of the VCF file located in "static/chat-details/".
    Returns:
        str: The extracted contact details in the format "Name|PhoneNumber",
             or "|" if extraction fails.
    """
    # Read file content
    try:
        with open(f"static/chat-details/{filename}", "r", encoding="utf-8") as file:
            vcf_content = file.read()
    except FileNotFoundError:
        return "|"
    # Extract name and number using regex
    fn_match = re.search(r"FN:(.+)", vcf_content)
    tel_match = re.search(r"TEL;type=.*?:\+?([\d\s]+)", vcf_content)

    if tel_match and fn_match:
        phone_number = tel_match.group(1).replace(" ", "").strip("\n")
        phone_number = "0" + phone_number[3:]
        return f"{fn_match.group(1)}|{phone_number}"
    else:
        return "|"


def verify_date(date):
    """
    Validates if a given string is a date that follows the format MM/DD/YY.
    Args:
        date (str): The date string to verify.
    Returns:
        bool: True if the date is valid, otherwise False.
    """
    try:
        datetime.strptime(date, "%m/%d/%y")
    except ValueError:
        return False
    else:
        return True

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
        # Text has been split into more than n parts
        last_part = ""
        # Merge all split parts together except the first n-1s
        for j in range(len(split_text)):
            if j < n-1:
                continue
            last_part += split_text[j] + delimiter
        final_split = split_text
        split_text = []
        for i in range(n-1):
            split_text.append(final_split[i])
        split_text.append(last_part)
    return split_text


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
    start_over = False
    msg_list = msg_list.copy()

    while True:
        for i in range(len(msg_list)):
            # In the unlikely case where the procedure is completed but 'start_over' doesn't change to False
            # This 3 lines will end the loop
            if stopped == len(msg_list):
                start_over = False
                continue
            # Skip messages that have already been checked
            if i < stopped:
                continue
            # If the current message isn't the start of a new one (It's the continuation of an old one.)
            if not verify_date(msg_list[i].split(", ")[0]):  #msg_list[i][0].isdigit() or msg_list[i][:8].count("/") != 2:
                if i == 0:
                    # File isn't a proper whatsapp chat file (The first message should be a new one)
                    raise TamperedFileError
                # Add the continuation message to the message before it and store in 'added'.
                added = msg_list[i - 1] + " " + msg_list[i]
                # Replace the message before the continuation message with 'added'
                msg_list[i - 1] = added
                # Remove the continuation message from the list
                msg_list.pop(i)
                # Reset variables so the function can properly look through the new list
                stopped = i
                start_over = True
                break
            start_over = False
        if start_over:
            # The 'msg_list' had been changed and the function needs to properly look through this new version
            continue
        break
    return msg_list


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
        # Split message into not more than 2 parts, timeframe(date and time) and message body(sender name and message content)
        temp_list = caution_split(i, " - ", 2)
        date, time = temp_list[0].split(", ")
        if ":" not in temp_list[1]:
            # Message is a whatsapp system notification/message (Not sent by a person)
            a_chat = {"date": datetime.strptime(date, "%m/%d/%y"), "time": time, "body": temp_list[1], "type": "info"}
            parsed_chat.append(a_chat)
            continue
        name, msg_body = caution_split(temp_list[1], ": ", 2)
        # Determine message types and edit message body where necessary.
        if "(file attached)" not in msg_body:
            msg_type = "text"
        elif msg_body[:3] == "STK":
            msg_type = "sticker"
        elif msg_body[:3] == "IMG":
            msg_type = "image"
            msg_body = msg_body.replace("(file attached)\n", "|")
        elif msg_body[:3] == "PTT" or msg_body[:3] == "AUD":
            msg_type = "audio"
        elif msg_body[:3] == "VID":
            msg_type = "video"
        elif ".vcf" in msg_body:
            msg_type = "contact"
            msg_body = extract_contact(msg_body.split(".vcf")[0] + ".vcf")
        elif ".pdf" in msg_body or ".PDF" in msg_body or detect_encrypted_pdf(f"static/chat-details/{msg_body.replace('(file attached)\n', '')}"):
            msg_type = "pdf"
            msg_body = msg_body.replace("(file attached)\n", "|")
            if msg_body[:3] == "DOC":
                msg_body = msg_body.replace(" |", "pdf")
        elif re.search(r"\b[\w\s()-]+\.[a-zA-Z0-9]{2,5}\b", msg_body) or "DOC" in msg_body:
            msg_type = "document"
        else:
            msg_type = "text"

        # More message body editing
        if msg_type != "text":
            msg_body = msg_body.replace("(file attached)\n", "|").strip(" ")
        if "<This message was edited>" in msg_body:
            edited = True
            msg_body = msg_body.removesuffix("<This message was edited>\n")
        else:
            edited = False
        if "Media omitted" in msg_body:
            msg_body = msg_body.replace("<", "")
        # Create dictionary containing message details
        a_chat = {"date": datetime.strptime(date, "%m/%d/%y"), "time": time, "name": name, "body": msg_body,
                  "type": msg_type, "edited": edited}
        parsed_chat.append(a_chat)
    return parsed_chat



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'


@app.route('/')
def welcome_user():
    """
    Renders the welcome page.
    Returns:
        Response: The rendered 'second.html' template.
    """
    return render_template("index.html")


@app.route("/upload", methods=["GET", "POST"])
def decipher():
    """
    Handles ZIP file uploads, extracts chat data, processes it, and renders name selection.
    Returns:
        Response: Renders the appropriate template based on success or failure.
    """
    if request.method == "POST":
        uploaded_file = request.files.get("zipFile")
        extract_zipfile(uploaded_file)
        files = get_files_by_extension("static/chat-details", ".txt")
        try:
            txt_content = find_and_read_chat_file(files)
            new = organize_msgs(txt_content)
        except FileNotFoundError:
            return render_template("error4xx.html")
        except TamperedFileError:
            return render_template("error5xx.html")
        chat_manager.set_chat(parse_chat(new))
        return render_template("pick-name.html", names=get_names(chat_manager.chat))
    return redirect(url_for('welcome_user'))


@app.route("/chat", methods=["POST"])
def render_chat():
    """
    Loads and renders the chat interface after verifying chat data and username.
    Returns:
        Response: Renders the chat page with GIFs or redirects if data is missing.
    """
    if request.method == "POST":
        if chat_manager.chat is None:
            return redirect(url_for('welcome_user'))
        name = request.form.get("username")
        chat_manager.set_name(name)
        try:
            with open(file="gifs.json", mode="r") as file:
                gifs = json.load(file)
        except FileNotFoundError:
            gif1 = ['../static/assets/gif/hello-cute-cat.gif', '../static/assets/gif/meme.gif',]
            gif2 = ['../static/assets/gif/kimetsu-no-yaiba.gif', '../static/assets/gif/eren-jaeger.gif']
        else:
            gif1 = gifs["gif1"]
            gif2 = gifs["gif2"]

        return render_template("chat.html", chat_manager=chat_manager, left_gifs=gif1, right_gifs=gif2)
    return redirect(url_for('welcome_user'))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
