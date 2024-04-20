from large import get_largest_obj
import socket
from sys import exit
import multiprocessing as mp
from datetime import datetime

OBJ_SEARCH_COUNT = 400
OBJ_SIZE_THRESH = 1500000
INFO_INTERVAL = 50

def find_object(website):

    try:
        dst_ip = socket.gethostbyname(website)
        (obj_size, obj_url) = get_largest_obj("https://" + website, dst_ip, 
                                              OBJ_SEARCH_COUNT, OBJ_SIZE_THRESH)
    except Exception:
        return ("ERR", "", "", 0)
    
    if obj_size < OBJ_SIZE_THRESH:
        return ("TOOSMALL", dst_ip, obj_url, obj_size)

    if not obj_url.startswith("https://"):
        return ("NOHTTPS", dst_ip, "", "")

    return ("OK", dst_ip, obj_url, obj_size)

def thr(work_q, result_q):
    import warnings
    from bs4 import GuessedAtParserWarning
    warnings.filterwarnings('ignore', category=GuessedAtParserWarning)
    while True:
        try:
            (cdn, website) = work_q.get()
        except ValueError: # Out of work
            exit(0)

        (status, dst_ip, obj_url, obj_size) = find_object(website)

        result_q.put((website, cdn, status, obj_size, dst_ip, obj_url))

def wr_thr(num_samples, result_q, resultfile):
    done = 0
    counts = {
        "OK": 0,
        "TOOSMALL": 0,
        "ERR": 0,
        "NOHTTPS": 0,
        "BADENCODE": 0,
    }

    with open(resultfile, "a") as f:
        while True:
            try:
                (website, cdn, status, obj_size, dst_ip, obj_url) = result_q.get()
            except ValueError:
                print("No results left, exiting", flush=True)
                exit(0)
            
            done += 1
            try:
                f.write(f"{website}, {cdn}, {status}, {obj_size}, {dst_ip}, {obj_url}\n")
            except UnicodeEncodeError:
                status = "BADENCODE"
                f.write(f"{website}, {cdn}, {status}, 0, {dst_ip}, \n")

            counts[status] += 1

            if done % INFO_INTERVAL == 0:
                print(f"[{datetime.now()}] ({done}/{num_samples}) OK: {counts['OK']}, TOOSMALL: {counts['TOOSMALL']}, ERR: {counts['ERR']}, NOHTTPS: {counts['NOHTTPS']}, BADENCODE:{counts['BADENCODE']}", flush=True)
                f.flush()

        

def run(numthreads, samplefile, resultfile):
    with open(samplefile) as f:
        lines = f.readlines()
        splits = [(line[:-1] if line.endswith('\n') else line).split(",") for line in lines]
        samples = [(split[2], split[0]) for split in splits]
    

    work_q = mp.Queue()
    result_q = mp.Queue()

    workers = [mp.Process(target=thr, args=(work_q, result_q)) for _ in range(numthreads)]
    for w in workers: w.start()

    writer_thr = mp.Process(target=wr_thr, args=(len(samples), result_q, resultfile))
    writer_thr.start()

    for sample in samples:
        work_q.put(sample)
    work_q.close()

    for w in workers: w.join()
    result_q.close()
    writer_thr.join()

if __name__ == "__main__":
    run(64, "sample.csv", "res-test.txt")





