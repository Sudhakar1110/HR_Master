<h3>Interview Feedback Submitted</h3>
<p>Dear {{ doc.owner }},</p>
<p>Interview feedback has been submitted for candidate <strong>{{ doc.candidate_name }}</strong>.</p>
<p><strong>Position:</strong> {{ doc.job_title }}</p>
<p><strong>Interviewer:</strong> {{ doc.interviewer }}</p>
<p><strong>Round:</strong> {{ doc.interview_round }}</p>
<p><strong>Overall Rating:</strong> {{ doc.overall_rating }}/5</p>
<p><strong>Recommendation:</strong> {{ doc.recommendation }}</p>
<p><strong>Result:</strong> {{ doc.result }}</p>
<br>
<p>View Feedback: <a href="/app/interview-feedback/{{ doc.name }}">{{ doc.name }}</a></p>
