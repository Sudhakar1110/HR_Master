<h3>Candidate Shortlisted</h3>
<p>Dear {{ doc.owner }},</p>
<p>Candidate <strong>{{ doc.candidate_name }}</strong> has been shortlisted for the position of <strong>{{ doc.job_title }}</strong>.</p>
<p><strong>Match Score:</strong> {{ doc.total_match_score }}%</p>
<p><strong>Recommendation:</strong> {{ doc.recommendation }}</p>
<br>
<p>Please proceed with the interview scheduling process.</p>
<p>View Ranking: <a href="/app/candidate-ranking/{{ doc.name }}">{{ doc.name }}</a></p>
