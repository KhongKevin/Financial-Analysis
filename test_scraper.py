try:
    from scraper import fetch_eps_data
    print("Import successful")
    data, error = fetch_eps_data("IBM")
    if error:
        print(f"Error: {error}")
    else:
        print(f"Success! Data points: {len(data)}")
        print(data[:3])
except Exception as e:
    print(f"Crash: {e}")
