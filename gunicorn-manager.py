import psutil, datetime, subprocess, requests, signal, pygit2
import streamlit as st
import pandas as pd

WORKING_DIR = "/home/ubuntu/<WORKING_DIR>/"
MAX_WORKER_PID = 4
def get_master_pid(WORKING_DIR = WORKING_DIR):
    try:
        with open(f"{WORKING_DIR}/app.pid", "r") as f:
            master_pid = int(f.read().strip())
        return master_pid
    except:
        return None
# function to get the master PID and worker PIDs separately
def get_pids():
    master_pid = get_master_pid()
    worker_pids = []
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        if process.info['cmdline'] and "gunicorn" in str(process.info['cmdline']):
            if "master" in str(process.info['cmdline']):
                master_pid = process.pid
            else:
                worker_pids.append(process.pid)
    if master_pid in worker_pids:
        worker_pids.remove(master_pid)
    return master_pid, worker_pids

# function to restart a worker process
def restart_worker(pid):
    _, worker_pids = get_pids()
    process = psutil.Process(pid)
    process.send_signal(signal.SIGTERM)
    st.warning(f"Restarting worker with PID {pid}")
    while True:
        _, new_worker_pids = get_pids()
        new_worker_pid = list(set(new_worker_pids) - set(worker_pids))
        if new_worker_pid and new_worker_pid[0] != pid:
            break
    st.success(f"Worker restarted successfully with PID {new_worker_pid}")
    return new_worker_pid

# function to restart the master process using HUP signal
def restart_master(master_pid):
    _, worker_pids = get_pids()
    process = psutil.Process(master_pid)
    process.send_signal(signal.SIGHUP)
    with st.spinner("Restarting master process..."):
        with st.warning(f"Restarting master process with PID {master_pid}"):
            while True:
                _, new_worker_pids = get_pids()
                # check if all the new_worker_pids is different from the old worker_pids
                if len(set(new_worker_pids) - set(worker_pids)) == len(new_worker_pids):
                    break
            st.success("Master process restarted successfully.")

    return new_worker_pids

def add_workers(num_workers=None):
    if not num_workers:
        num_workers = st.session_state.add_workers
    master_pid, _ = get_pids()
    if len(_) >= MAX_WORKER_PID:
        st.warning(f"Maximum number of workers reached. Cannot add more workers.")
        return
    num_workers = min(num_workers, MAX_WORKER_PID - len(_))
    process = psutil.Process(master_pid)
    for _ in range(num_workers):
        with st.spinner(f"Adding worker {_+1}/{num_workers} to master process with PID {master_pid}"):
            process.send_signal(signal.SIGTTIN)
            process.send_signal(signal.SIGWINCH)


def remove_workers(num_workers=None):
    if not num_workers:
        num_workers = st.session_state.remove_workers
    master_pid, _ = get_pids()
    process = psutil.Process(master_pid)
    for _ in range(num_workers):
        with st.spinner(f"Removing worker {_+1}/{num_workers} from master process with PID {master_pid}"):
            process.send_signal(signal.SIGTTOU)
            process.send_signal(signal.SIGWINCH)

# function to kill the master process
def kill_master(pid):
    process = psutil.Process(pid)
    process.kill()
    st.success(f"Killed master process with PID {pid}")
    return True

# function to test the master process by calling localhost:5000/api/devops API
def test_master():
    try:
        response = requests.get("http://localhost:5001/api/devops")
        if response.status_code == 200:
            st.success("Master process is running.")
        else:
            st.warning("Master process is not running.")
    except:
        st.error("Unable to connect to the master process.")

# function to display memory usage for a process
def display_memory_usage(pid):
    process = psutil.Process(pid)
    memory_info = process.memory_info()
    memory_usage = memory_info.rss / (1024 * 1024)
    return memory_usage

def display_pid_table(pid_list):
    col_names = list(pid_list[0].keys()) + ["Restart"]
    table_rows =  [list(i.values()) for i in pid_list]
    col_widths = [3, 3, 4, 4, 5, 5]
    table_rows.insert(0, col_names)
    cols = st.columns(col_widths)
    for j,value in enumerate(col_names):
        cols[j].write(value)
    
    for row in table_rows[1:]:
        worker_pid = row[0]
        cols = st.columns(col_widths)
        restart_button = cols[-1].empty()
        do_restart = restart_button.button(f"Restart {worker_pid}")
        if do_restart:
            restart_worker(worker_pid)
            st.experimental_rerun()
        for j, value in enumerate(row):
            cols[j].write(value)

def start_master():
    with st.spinner("Starting master process..."):
        subprocess.Popen(["sudo", "systemctl", "start", "gunicorn.service"])
        st.success("Master process started successfully.")

def get_current_branch_name():
    repo = pygit2.Repository(WORKING_DIR)
    branch_name = repo.head.shorthand
    return branch_name

def change_branch(branch_name=None):
    if not branch_name:
        branch_name = st.session_state.branch_name
    pull_changes()
    with st.spinner("Checking out branch..."):
        subprocess.check_output(["git", "checkout", branch_name], cwd=WORKING_DIR)
        st.success(f"Checked out branch {branch_name}")

def pull_changes():
    with st.spinner("Pulling changes from remote..."):
        subprocess.check_output(["git", "pull"], cwd=WORKING_DIR)
        st.success("Pulled changes from remote.")

def get_all_branch_name():
    repo = pygit2.Repository(WORKING_DIR)
    branches = repo.listall_branches()
    return branches

def total_memory_available():
    mem = psutil.virtual_memory()
    total_memory = mem.total / (1024 * 1024)
    remaining_memory = mem.available / (1024 * 1024)


    if 1-(remaining_memory / total_memory) < 0.5:
        colour = "green"
    elif 1-(remaining_memory / total_memory) < 0.70:
        colour = "yellow"
    elif 1-(remaining_memory / total_memory) < 0.85:
        colour = "orange"
    else:
        colour = "red"
    st.markdown(f"""<style>.stProgress .st-bg {{background-color: {colour};}}</style>""", unsafe_allow_html=True)
    progress_bar = st.progress(0)
    progress_bar.progress(value=round(1-(remaining_memory / total_memory),2), text="Memory availabe: {:.2f} MB / {:.2f} MB".format(remaining_memory, total_memory))


def find_is_master_alive():
    master_pid, _ = get_pids()
    if master_pid:
        return True
    else:
        return False


def main(master_pid, worker_pid):
    # GitLab Ops
    st.header("GitLab Ops", help = "Use it to manage your GitLab repository.")
    current_branch_name = get_current_branch_name()
    st.info(f"Current branch: {current_branch_name}", icon ="ℹ️")
    all_branch_names = get_all_branch_name()
    branch_names = [i for i in current_branch_name if i != all_branch_names]
    if branch_names:
        st.selectbox("Select branch to change to", all_branch_names, on_change = change_branch, key = "branch_name")
    if st.button("Pull Changes"):
        pull_changes()
        st.experimental_rerun()
    ##########

    # Master Process Ops
    st.header("Gunicorn Master Process 🔥", help = "Master Process Manager")
    st.warning(f"Master process PID: {master_pid}", icon = "💀")
    st.info(f"Memory Usage: {display_memory_usage(master_pid):.2f} MB", icon = "📈")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Restart Master", key="restart_master"):
            restart_master(master_pid)
            st.experimental_rerun()
    with col2:
        if st.button("Kill Master", key="kill_master"):
            kill_master(master_pid)
    with col3:
        if st.button("Test Master", key="test_master"):
            test_master()
    with col4:
        if st.button("Refresh", key="refresh"):
            st.experimental_rerun()
    ##########
    
    # Worker Process Ops
    st.header(f"{len(worker_pids)} Worker processes 🤖", help = f"List of Worker Processs")
    col1, col2 = st.columns(2)
    with col1:
        num_workers = st.number_input("Add Workers:", max_value=MAX_WORKER_PID, min_value=0, value = 0, key = "add_workers", help = f"Maximum number of workers is {MAX_WORKER_PID}", step = 1)
        if num_workers:
            add_workers(num_workers)
            st.session_state.pop("add_workers")
            st.experimental_rerun()

    with col2:
        num_workers = st.number_input("Remove Workers:", max_value=len(worker_pids), min_value=0, value = 0, key = "remove_workers", help = f"Minimum number of workers is {len(worker_pids)-1}", step = 1)
        if num_workers:
            remove_workers(num_workers)
            st.session_state.pop("remove_workers")
            st.experimental_rerun()
    
    if not worker_pids:
        st.warning("No workers found", icon = "🚨")

    df = pd.DataFrame(worker_pids, columns = ["PID"])
    df["process"] = df["PID"].apply(lambda x: psutil.Process(x))
    df["Status"] = df["process"].apply(lambda x: x.status().capitalize())
    df["Active Threads/Total Threads"] = df["process"].apply(lambda x: f"{x.num_threads() - x.num_threads() * x.cpu_percent(interval=None) / 100}/{x.num_threads()}")
    df["Memory Usage (MB)"] = df["process"].apply(lambda x: round(x.memory_info().rss / (1024 * 1024), 2))
    df["Time Elapsed"] = df["process"].apply(lambda x: datetime.datetime.fromtimestamp(x.create_time()))
    df["days"] = df["Time Elapsed"].apply(lambda x: (datetime.datetime.now() - x).days)
    df["hours"] = df["Time Elapsed"].apply(lambda x: (datetime.datetime.now() - x).seconds // 3600)
    df["minutes"] = df["Time Elapsed"].apply(lambda x: (datetime.datetime.now() - x).seconds % 3600 // 60)
    df["seconds"] = df["Time Elapsed"].apply(lambda x: (datetime.datetime.now() - x).seconds % 60)
    df["Created Time"] = df.apply(lambda x: f"{str(x['days']) + ' day ' if x['days'] == 1 else str(x['days'] + ' day ' if x['days']>1 else '')}{str(x['hours']) + ' hour ' if x['hours'] == 1 else str(x['hours']) + ' hours ' if x['hours'] > 1 else ''}{str(x['minutes']) + ' minute ' if x['minutes'] == 1 else str(x['minutes']) + ' minutes ' if x['minutes'] > 1 else ''}{str(x['seconds']) + ' second ' if x['seconds'] == 1 else str(x['seconds']) + ' seconds ' if x['seconds'] > 1 else ''}" + "Ago", axis = 1)
    df = df.sort_values(by = "Time Elapsed", ascending = False)
    df = df.drop(["process", "Time Elapsed", "days", "hours", "minutes", "seconds"], axis = 1)
    table_data = df.to_dict("records")
    display_pid_table(table_data)
    ##########



st.title("Deeplearning Manager")
total_memory_available()
master_is_alive = find_is_master_alive()
if not master_is_alive:
    st.error("No master process found.")
    if st.button("Start Master", key="start_master"):
        start_master()
master_pid, worker_pids = get_pids()
main(master_pid, worker_pids)


