# Living Inbox – One-brain Workspace POC

**A simple AI-powered project memory and living inbox prototype**

## What this project does

This is a proof-of-concept (POC) application that tries to create a "second brain" for project work.  
The main idea:  
Instead of searching through emails, Slack, notes, or Jira every time, you type a project ID → and all important context appears automatically.

### Core Features (what actually works right now)

1. **Project Memory / Query**  
   - You type a project ID (e.g. `PRJ-003`)  
   - The app shows:  
     - Project name, client name, assigned developer  
     - Health status (🟢 On Track, 🟡 At Risk, 🔴 Blocked)  
     - Priority, due date  
     - Full project description  
     - All notes/activities you added earlier (visible in "Activity History")  
   - Data comes from a vector database (Pinecone) that remembers everything

2. **Living Inbox (manual version)**  
   - Go to Inbox tab  
   - Type project ID + paste any note, email snippet, chat message  
   - Click "Append to Context"  
   - The note gets saved with timestamp → next time you query the project, it appears in Activity History  
   - This is the "living" part: the project memory keeps growing as you add updates

3. **Explore / Team View**  
   - See all projects for a specific customer or developer  
   - Type developer ID (e.g. `DEV-001`) or customer ID  
   - Shows list of projects with names, health, priority, due date, developer name

4. **Intent → Plan (basic version)**  
   - Describe what you want to do (e.g. "Prepare demo for PeakPulse next week")  
   - AI generates a simple markdown plan:  
     - Likely related project  
     - Numbered tasks  
     - Suggested owner (using real developer names)  
     - Deadline/urgency  
     - Possible blockers

### How the system works (simple flow)

1. Project info lives in `data.json`  
2. Run `ingest.py` → sends all projects to Pinecone (smart searchable memory)  
3. Run `streamlit run app.py` → opens the web app  
4. You interact:  
   - Add notes → saved forever per project  
   - Query ID → see full context + history  
   - Ask AI for plans → gets basic task list

### Current status (February 2026)

| Feature               | Status     | Comment                                                                 |
|-----------------------|------------|-------------------------------------------------------------------------|
| Query by project ID   | ✅ Working | Shows details + all added notes                                         |
| Add notes (Inbox)     | ✅ Working | Notes appear in Activity History after append                           |
| Activity history view | ✅ Working | Shows timestamp + content of every note you added                       |
| Explore (by dev/cust) | ✅ Working | Shows project list with correct names (after fixes)                     |
| Intent → Plan         | ✅ Working | Generates basic markdown task list (after tab was restored) |

Future Tasks :
            
| Auto-update status    | ❌ Not yet | Health/priority still static – no AI analysis of new notes              |
| Email/chat auto-import| ❌ Not yet | Currently manual paste only                                             |
| Real team learning    | ❌ Not yet | No similarity search for past solutions or duplicate prevention         |

