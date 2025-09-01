import csv
import openrouteservice

def geocode_addresses(input_csv, output_csv, ors_key):
    client = openrouteservice.Client(key=ors_key)

    with open(input_csv, newline="", encoding="utf-8") as f_in, \
         open(output_csv, "w", newline="", encoding="utf-8") as f_out:
        
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames + ["lat", "lon"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            addr = row["address"]
            try:
                res = client.pelias_search(addr, size=1)
                if res["features"]:
                    coords = res["features"][0]["geometry"]["coordinates"]
                    row["lon"], row["lat"] = coords[0], coords[1]
                else:
                    row["lon"], row["lat"] = "", ""
            except Exception as e:
                print(f"Geocoding failed for {addr}: {e}")
                row["lon"], row["lat"] = "", ""
            writer.writerow(row)

    print(f"✅ Output written to {output_csv}")


if __name__ == "__main__":
    ORS_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImJmNmI4YjljODBjODQ5YzZhZGRlNTk4ZWE5ZjY2M2E3IiwiaCI6Im11cm11cjY0In0="
    geocode_addresses("students_with_addresses.csv", "students.csv", ORS_KEY)
