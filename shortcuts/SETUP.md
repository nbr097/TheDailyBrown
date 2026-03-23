# iOS Shortcuts Setup

Three Shortcuts automate your Morning Briefing. Create each one in the **Shortcuts** app on your iPhone.

---

## 1. Morning Briefing Trigger (Charger Disconnect)

This shortcut fires when you unplug your phone in the morning, triggering the briefing.

### Steps to create

1. Open **Shortcuts** > **Automation** > **+** > **Create Personal Automation**
2. Select **Charger** > **Is Disconnected** > **Next**
3. Add action: **Get Current Location**
4. Add action: **Get Contents of URL**
   - URL: `https://morning.yourdomain.com/summary?lat={Latitude}&lon={Longitude}`
   - Method: **GET**
   - Headers:
     - `Authorization`: `Bearer YOUR_BEARER_TOKEN`
5. Add action: **Open URL**
   - URL: `https://morning.yourdomain.com/dashboard/`
6. Tap **Next**
7. **Disable** "Ask Before Running"
8. Tap **Done**

### Notes
- Replace `morning.yourdomain.com` with your actual Cloudflare tunnel domain
- Replace `YOUR_BEARER_TOKEN` with the token from `install.sh` output
- The GET request warms the cache so the dashboard loads instantly

---

## 2. Morning Briefing Fallback (6:30 AM Time Trigger)

A backup trigger in case you forget to unplug or charge overnight.

### Steps to create

1. Open **Shortcuts** > **Automation** > **+** > **Create Personal Automation**
2. Select **Time of Day** > set to **6:30 AM** > **Daily** > **Next**
3. Add action: **Get Current Location**
4. Add action: **Get Contents of URL**
   - URL: `https://morning.yourdomain.com/summary?lat={Latitude}&lon={Longitude}`
   - Method: **GET**
   - Headers:
     - `Authorization`: `Bearer YOUR_BEARER_TOKEN`
5. Add action: **Show Notification**
   - Title: `Morning Briefing`
   - Body: `Your briefing is ready. Tap to open.`
6. Tap **Next**
7. **Disable** "Ask Before Running"
8. Tap **Done**

### Notes
- Adjust the time to match your typical wake-up
- The notification provides a non-intrusive prompt

---

## 3. Reminders Push (4:00 AM Daily)

This shortcut runs at 4:00 AM, gathers today's Reminders, and pushes them to the Morning Briefing API so they appear on the dashboard.

### Steps to create

1. Open **Shortcuts** > **Automation** > **+** > **Create Personal Automation**
2. Select **Time of Day** > set to **4:00 AM** > **Daily** > **Next**
3. Add action: **Find Reminders Where**
   - Filter: **Due Date** is **Today**
   - Filter: **Is Completed** is **No**
4. Add action: **Repeat with Each** (item in Reminders)
   - Inside the loop, add **Text** action:
     ```
     {"title": "{Name}", "due": "{Due Date}", "list": "{List}"}
     ```
   - Add action: **Add to Variable** > variable name: `reminderItems`
5. After the loop, add **Text** action:
   ```
   {"reminders": [{reminderItems}]}
   ```
   - Use **Combine Text** with separator `,` on the variable before inserting
6. Add action: **Get Contents of URL**
   - URL: `https://morning.yourdomain.com/data/reminders`
   - Method: **POST**
   - Headers:
     - `Authorization`: `Bearer YOUR_BEARER_TOKEN`
     - `Content-Type`: `application/json`
   - Request Body: **File** > select the Text from step 5
7. Tap **Next**
8. **Disable** "Ask Before Running"
9. Tap **Done**

### Detailed Shortcut Assembly

If the above is tricky with variables, here is a simpler approach:

1. **Find Reminders** where Due Date is Today and Is Completed is No
2. **Set Variable** `allReminders` to the found reminders
3. **Text** block — build JSON manually:
   ```
   {"reminders": []}
   ```
4. Use a **Repeat** loop over `allReminders`, appending each to a list variable
5. Use **Replace Text** to insert the comma-separated items into the JSON array
6. **Get Contents of URL** — POST the final JSON to `/data/reminders`

### Notes
- The 4:00 AM time ensures reminders are available before you wake up
- The `/data/reminders` endpoint stores them for the day
- Reminders are shown on the dashboard in the "Reminders" card

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| "Could not connect" | Verify your Cloudflare tunnel is running (`docker compose logs cloudflared`) |
| Auth error (401) | Double-check the Bearer token matches your `.env` file |
| Location unavailable | Ensure Shortcuts has location permission in Settings > Privacy |
| Reminders not showing | Check that the POST to `/data/reminders` returns 200; verify `BEARER_TOKEN` |
| Automation not firing | Ensure "Ask Before Running" is disabled; restart your iPhone |
