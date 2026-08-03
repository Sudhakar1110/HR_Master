<h3>Interview Scheduled</h3>
<p>Dear {{ doc.owner }},</p>
<p>An interview has been scheduled for candidate <strong>{{ doc.candidate_name }}</strong>.</p>
<p><strong>Job:</strong> {{ doc.job_title }}</p>
<p><strong>Date:</strong> {{ doc.scheduled_date }}</p>
<p><strong>Time:</strong> {{ doc.scheduled_time }}</p>
<p><strong>Mode:</strong> {{ doc.mode_of_interview }}</p>
<p><strong>Round:</strong> {{ doc.interview_round }}</p>
<br>
<p>View Schedule: <a href="/app/interview-schedule/{{ doc.name }}">{{ doc.name }}</a></p>
