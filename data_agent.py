import os
import zmq
import json
import urllib.request
import urllib.parse
import re
import html
import datetime
import wikipedia

DOC_DIR = os.path.join(os.getcwd(), "documents")
if not os.path.exists(DOC_DIR):
    os.makedirs(DOC_DIR)

def scrape_duckduckgo(query):
    """
    Scrapes DuckDuckGo HTML results securely using standard Python urllib and regular expressions.
    No extra external scraping dependencies required!
    """
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw_html = response.read().decode('utf-8', errors='ignore')
            
        # Parse search results:
        # A result typically is contained within result divs.
        # Let's find result titles, URLs and snippets
        # DDG HTML search results have class="result__a", class="result__snippet" and class="result__url"
        
        # Extract title link tags and snippets using attribute-order-independent regexes
        title_matches = re.findall(r'<a\b[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw_html, re.DOTALL)
        snippet_matches = re.findall(r'<a\b[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', raw_html, re.DOTALL)
        
        results = []
        for i in range(min(5, len(title_matches))):
            raw_url, raw_title = title_matches[i]
            
            # Clean up URL (sometimes DDG wraps external links)
            parsed_url = raw_url
            if "uddg=" in raw_url:
                parsed_url = urllib.parse.unquote(raw_url.split("uddg=")[1].split("&")[0])
                
            # Clean up title and snippet HTML tags and unescape entities
            clean_title = html.unescape(re.sub(r'<[^>]+>', '', raw_title)).strip()
            
            clean_snippet = ""
            if i < len(snippet_matches):
                clean_snippet = html.unescape(re.sub(r'<[^>]+>', '', snippet_matches[i])).strip()
                
            results.append({
                "title": clean_title,
                "url": parsed_url,
                "snippet": clean_snippet
            })
            
        return results
    except Exception as e:
        print(f"Error scraping DuckDuckGo: {e}")
        return []

def collect_and_compile(topic):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Fetch Wikipedia Summary
    wiki_summary = "No direct Wikipedia entry found."
    wiki_url = "N/A"
    try:
        # Search first to get best page title, avoiding direct DisambiguationError
        search_results = wikipedia.search(topic)
        best_match = search_results[0] if search_results else topic
        wiki_summary = wikipedia.summary(best_match, sentences=5)
        try:
            wiki_page = wikipedia.page(best_match)
            wiki_url = wiki_page.url
        except Exception:
            pass
    except Exception as e:
        print(f"Wikipedia lookup error for topic '{topic}': {e}")
        
    # 2. Fetch Web search results
    web_results = scrape_duckduckgo(topic)
    
    # 3. Create document content
    content_lines = [
        "==================================================",
        "          J.A.R.V.I.S. INTELLIGENCE REPORT        ",
        f"Topic:     {topic}",
        f"Generated: {timestamp}",
        "==================================================\n",
        "[SECTION 1: ENCYCLOPEDIC SUMMARY (WIKIPEDIA)]",
        f"Source: {wiki_url}\n",
        wiki_summary,
        "\n" + "-" * 50 + "\n",
        "[SECTION 2: LIVE WEB SEARCH RESULTS]",
        f"Query: '{topic}' via DuckDuckGo\n"
    ]
    
    if web_results:
        for idx, res in enumerate(web_results, 1):
            content_lines.append(f"{idx}. {res['title']}")
            content_lines.append(f"   URL:     {res['url']}")
            content_lines.append(f"   Summary: {res['snippet']}\n")
    else:
        content_lines.append("No live web search results could be retrieved at this time.")
        
    content_lines.append("\n==================================================")
    content_lines.append("               END OF INTELLIGENCE REPORT         ")
    content_lines.append("==================================================")
    
    report_content = "\n".join(content_lines)
    
    # 4. Save to files
    safe_topic_name = re.sub(r'[^\w\s-]', '', topic).strip().replace(" ", "_").lower()
    filename = f"collection_{safe_topic_name}.txt"
    filepath = os.path.join(DOC_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return filename, filepath, wiki_summary, wiki_url
    except Exception as e:
        raise IOError(f"Could not save intelligence report to disk: {e}")

def process_command(cmd):
    action = cmd.get("action")
    topic = cmd.get("topic")
    
    if action == "collect":
        if not topic:
            return "No topic provided for data collection, sir."
            
        try:
            filename, filepath, wiki_summary, wiki_url = collect_and_compile(topic)
            return (
                f"Sir, I have gathered comprehensive intelligence on '{topic}'. "
                f"The report has been compiled and saved as '{filename}' inside your documents directory. "
                f"Wikipedia Source: {wiki_url}. "
                f"Wikipedia Summary: {wiki_summary}"
            )
        except Exception as e:
            return f"I encountered an error compiling the data, sir: {str(e)}"
            
    elif action == "show_collected":
        try:
            if not os.path.exists(DOC_DIR):
                return "Sir, you have not collected any data reports yet. Use the command 'collect data on [topic]' to start."
            files = [f for f in os.listdir(DOC_DIR) if f.startswith("collection_") and f.endswith(".txt")]
            if not files:
                return "Sir, you have not collected any data reports yet. Use the command 'collect data on [topic]' to start."
            
            topics = []
            for f in files:
                topic_name = f.replace("collection_", "").replace(".txt", "").replace("_", " ").title()
                topics.append(f"'{topic_name}' (File: {f})")
                
            list_str = "\n- ".join(topics)
            return f"Sir, here are all the intelligence reports I have compiled for you:\n- {list_str}"
        except Exception as e:
            return f"I had trouble retrieving the list of reports, sir: {str(e)}"
            
    return "Unknown data agent command."

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5562")

    print("Data Collection Agent started. Listening on port 5562...")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
        except Exception as e:
            response = f"Data Collection Agent Error: {str(e)}"
            
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
