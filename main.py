from workers_breakdown import run_breakdown_for_all_users

if __name__ == "__main__":
    results = run_breakdown_for_all_users(limit_per_user=10)
    print("Breakdown results per user:", results)