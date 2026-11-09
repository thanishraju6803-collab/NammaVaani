# NammaVaani — Mandi CSV guide (no API key)

## Where to get the file

1. Open the official Government of India Agmarknet daily market-price resource:
   https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
2. Use the **CSV Download** option on the resource page. If the page offers filters or export settings, choose the required date range and Karnataka (or a larger export that includes Karnataka).
3. Save the downloaded file somewhere easy to find, such as Downloads.

The dataset contains reported wholesale minimum, maximum and modal prices. The OGD catalogue describes it as daily data generated through AGMARKNET. Check the resource page for the current data update date and dataset licence before redistribution.

## Load it into NammaVaani

1. Start NammaVaani with `streamlit run app.py`.
2. Open **Mandi Prices**.
3. Select a commodity and district.
4. Upload the downloaded `.csv` file.
5. Click **Find prices**.
6. If the results are correct, click **Save this CSV for future use**. It is saved to `data/mandi_prices.csv` by default.

You only need to upload again when you download a newer CSV. NammaVaani does not automatically refresh the local file.

## Expected columns

The importer recognises common variants of these headings:

```csv
State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min Price,Max Price,Modal Price
```

Headers may contain spaces, underscores, case differences, or appended units such as `Min Price (Rs/Quintal)`.

## Data safety

- The CSV must contain actual Agmarknet rows. The included `data/mandi_prices_template.csv` is only a blank header template; it contains no prices.
- NammaVaani filters by state, district and commodity.
- The arrival date is displayed for every result. Records older than three days are visibly marked as older data.
- These are reported wholesale mandi observations, not guaranteed farm-gate prices or the price a farmer will necessarily receive.
- If no matching record is found, the app reports that result. It does not create sample prices.
- Follow the dataset licence and attribution conditions on the OGD resource page.
