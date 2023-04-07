import psutil, datetime, subprocess,time
import streamlit as st
import requests
import signal, pygit2

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

def display_logs():
    st.header("Gunicorn logs")
    logs_process_1 = subprocess.Popen(["tail", "-f", "server.log"], stdout=subprocess.PIPE)
    logs_process_2 = subprocess.Popen(["tail", "-f", "error.log"], stdout=subprocess.PIPE)
    logs_process_3 = subprocess.Popen(["tail", "-f", "access.log"], stdout=subprocess.PIPE)
    with st.container():
        while True:
            if st.button("Stop logs", key = f"stop_logs_{datetime.datetime.now()}", help = "Stop the logs from streaming"):
                break
            output_1 = logs_process_1.stdout.readline().decode()
            output_2 = logs_process_2.stdout.readline().decode()
            output_3 = logs_process_3.stdout.readline().decode()
            if not output_1 and not output_2 and not output_3:
                break
            if output_1:
                st.write(output_1.strip())
            if output_2:
                st.write(output_2.strip())
            if output_3:
                st.write(output_3.strip())

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

def add_workers(num_workers):
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


def remove_workers(num_workers):
    master_pid, _ = get_pids()
    process = psutil.Process(master_pid)
    for _ in range(num_workers):
        with st.spinner(f"Removing worker {_+1}/{num_workers} from master process with PID {master_pid}"):
            process.send_signal(signal.SIGTTOU)
            process.send_signal(signal.SIGWINCH)
    st.experimental_rerun()

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
    st.write(f"Memory usage for PID {pid}: {memory_usage:.2f} MB")

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

def get_branch_name():
    repo = pygit2.Repository(WORKING_DIR)
    branch_name = repo.head.shorthand
    return branch_name

def change_branch(branch_name):
    pull_changes()
    subprocess.check_output(["git", "checkout", branch_name], cwd=WORKING_DIR)

def pull_changes():
    subprocess.check_output(["git", "pull"], cwd=WORKING_DIR)

def get_branch_names():
    repo = pygit2.Repository(WORKING_DIR)
    branches = repo.listall_branches()
    return branches


def main(dead = False):
    st.title("Gunicorn Manager")
    st.header("Master process")
    if dead:
        st.error("No master process found.")
        if st.button("Start Master"):
            start_master()
            st.experimental_rerun()
            return

    branch_name = get_branch_name()
    st.write(f"Current branch: {branch_name}")
    branch_names = get_branch_names()
    branch_names = [i for i in branch_names if i != branch_name]
    if branch_names:
        col1, col2 = st.columns(2)
        with col1:
            new_branch_name = col1.selectbox("Select branch to change to", branch_names)
        with col2:
            if col2.button("Change Branch"):
                change_branch(new_branch_name)
                st.experimental_rerun()
                return
    master_pid, worker_pids = get_pids()
    if master_pid:
        st.write(f"Master process PID: {master_pid}")
        col1, col2, col3 = st.columns(3)
        try:
            display_memory_usage(master_pid)
        except:
            return main(dead = True)
        with col1:
            if st.button("Restart Master"):
                restart_master(master_pid)
                st.experimental_rerun()
                return
        with col2:
            if st.button("Kill Master"):
                kill_master(master_pid)
                return
        with col3:
            if st.button("Test Master"):
                test_master()

    else:
        return main(dead = True)
    
    st.header(f"{len(worker_pids)} Worker processes")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Add/Remove Workers")
    with col2:
        if st.button("Refresh"):
            st.experimental_rerun()
            return
    col1, col2 = st.columns(2)
    with col1:
        num_workers = st.number_input("Add Workers:", max_value=MAX_WORKER_PID, min_value=0, value = 0, key = "add_workers")
        if num_workers:
            add_workers(num_workers)
            st.session_state.clear()

    with col2:
        num_workers = st.number_input("Remove Workers:", max_value=len(worker_pids), min_value=0, value = 0, key = "remove_workers")
        if num_workers:
            remove_workers(num_workers)
            st.session_state.clear()


        

    if worker_pids:
        table_data = []
        for worker_pid in worker_pids:
            process = psutil.Process(worker_pid)
            process_create_time = datetime.datetime.fromtimestamp(process.create_time())
            time_elapsed = datetime.datetime.now() - process_create_time
            time_elapsed_str = ""
            if time_elapsed.days > 0:
                time_elapsed_str += f"{time_elapsed.days} day{'s' if time_elapsed.days > 1 else ''}"
            if time_elapsed.seconds >= 3600:
                hours = time_elapsed.seconds // 3600
                time_elapsed_str += f"{hours} hour{'s' if hours > 1 else ''}"
            if time_elapsed.seconds % 3600 >= 60:
                minutes = (time_elapsed.seconds % 3600) // 60
                time_elapsed_str += f"{minutes} minute{'s' if minutes > 1 else ''}"

            else:
                time_elapsed_str += f"{time_elapsed.seconds % 60} second{'s' if time_elapsed.seconds % 60 > 1 else ''}"
            time_elapsed_str += " Ago"
            table_data.append({
                "PID": worker_pid,
                "Status": process.status().capitalize(),
                "Active Threads/Total Threads": f"{process.num_threads() - process.num_threads() * process.cpu_percent(interval=None) / 100}/{process.num_threads()}",
                "Memory Usage (MB)": round(process.memory_info().rss / (1024 * 1024), 2),
                "Created Time": time_elapsed_str,
                "Time_elapsed": process.create_time()
            })
            # sort table data by elapsed time in ascending order
        table_data = sorted(table_data, key=lambda x: x["Time_elapsed"], reverse=True)
        # delete the time_elapsed key
        for i in table_data:
            del i["Time_elapsed"]

        display_pid_table(table_data)
    else:
        st.write("No worker processes found.")
    # display_logs()

if __name__ == "__main__":
    main()
