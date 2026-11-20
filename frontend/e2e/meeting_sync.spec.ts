import { test, expect } from "@playwright/test";

test.describe("Level 10 Real-Time Meeting Synchronization Across Two Browsers", () => {
  test("Facilitator advances the agenda, the second browser follows, and both see the summary", async ({
    browser,
  }) => {
    // Context 1: Facilitator (u2 - Blake Brooks, Team Member on team_lead)
    const facilitatorContext = await browser.newContext();
    await facilitatorContext.addInitScript(() => {
      localStorage.setItem("ninety_user_id", "u2");
    });
    const pageFacilitator = await facilitatorContext.newPage();

    // Context 2: Attendee (u3 - Casey Cho, Team Member on team_lead)
    const attendeeContext = await browser.newContext();
    await attendeeContext.addInitScript(() => {
      localStorage.setItem("ninety_user_id", "u3");
    });
    const pageAttendee = await attendeeContext.newPage();

    // 1. Facilitator navigates to the team page
    await pageFacilitator.goto("/teams/team_lead");
    await expect(pageFacilitator.locator("h1")).toContainText("Leadership");

    // 2. Facilitator starts (or joins) the Level 10 Meeting
    const meetingBtn = pageFacilitator.locator("header button", {
      hasText: /Start Level 10|Join Live Meeting/,
    });
    await expect(meetingBtn).toBeVisible();
    await meetingBtn.click();

    // Verify the facilitator is in the meeting room (Scorecard phase)
    await expect(pageFacilitator).toHaveURL(/\/teams\/team_lead\/meeting/);
    await expect(pageFacilitator.locator("text=Scorecard Phase")).toBeVisible();
    await expect(pageFacilitator.locator("text=Facilitator:")).toContainText("Blake Brooks");

    // 3. Attendee joins from their own browser
    await pageAttendee.goto("/teams/team_lead/meeting");
    await expect(pageAttendee.locator("text=Scorecard Phase")).toBeVisible();
    await expect(pageAttendee.locator("text=In Room:")).toBeVisible();
    await expect(pageAttendee.getByText("Casey Cho", { exact: true }).last()).toBeVisible();

    // The attendee is not the facilitator and must not get facilitator controls
    await expect(pageAttendee.locator("button", { hasText: "Next Section" })).toHaveCount(0);

    // 4. Facilitator advances to IDS
    const nextBtn = pageFacilitator.locator("button", { hasText: "Next Section" });
    await expect(nextBtn).toBeVisible();
    await nextBtn.click();
    await expect(pageFacilitator.locator("text=IDS Phase")).toBeVisible();

    // 5. Second browser follows within ~1 second (real-time sync)
    await expect(pageAttendee.locator("text=IDS Phase")).toBeVisible({ timeout: 5000 });
    await expect(pageAttendee.locator("text=Identify, Discuss, Solve")).toBeVisible();

    // 6. Facilitator advances to Conclude
    await nextBtn.click();
    await expect(pageFacilitator.locator("text=Conclude Phase")).toBeVisible();

    // 7. Second browser follows to Conclude
    await expect(pageAttendee.locator("text=Conclude Phase")).toBeVisible({ timeout: 5000 });
    await expect(pageAttendee.locator("text=Rate This Meeting")).toBeVisible();

    // 8. Attendee rates the meeting; the facilitator sees the rating live
    await pageAttendee
      .getByRole("button", { name: "9", exact: true })
      .click();
    await expect(pageAttendee.locator("text=Your submitted rating: 9 / 10")).toBeVisible();
    await expect(pageFacilitator.locator("text=Casey Cho: 9 ★")).toBeVisible({ timeout: 5000 });

    // 9. Facilitator ends the meeting; both browsers land on the summary
    pageFacilitator.on("dialog", (dialog) => dialog.accept());
    await pageFacilitator.locator("button", { hasText: "End" }).last().click();

    await expect(pageFacilitator.locator("text=Level 10 Meeting Summary")).toBeVisible({ timeout: 5000 });
    await expect(pageAttendee.locator("text=Level 10 Meeting Summary")).toBeVisible({ timeout: 5000 });
    await expect(pageAttendee.locator("text=9 / 10")).toBeVisible();
    await expect(pageFacilitator.locator("text=Meeting Completed")).toBeVisible();

    // 10. A refresh still shows the finished meeting summary (late joins / reconnects)
    await pageAttendee.reload();
    await expect(pageAttendee.locator("text=Level 10 Meeting Summary")).toBeVisible({ timeout: 5000 });

    await facilitatorContext.close();
    await attendeeContext.close();
  });
});
