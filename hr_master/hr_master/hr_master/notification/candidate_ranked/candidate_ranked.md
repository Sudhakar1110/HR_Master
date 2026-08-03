<h3>Candidate Ranked</h3>
<p>Dear {{ doc.owner }},</p>
<p>Candidate <strong>{{ doc.candidate_name }}</strong> has been ranked for the position <strong>{{ doc.job_title }}</strong>.</p>
<p><strong>Match Score:</strong> {{ doc.total_match_score }}%</p>
<p><strong>Recommendation:</strong> {{ doc.recommendation }}</p>
<p><strong>Status:</strong> {{ doc.status }}</p>
<br>
<p>View Ranking: <a href="/app/candidate-ranking/{{ doc.name }}">{{ doc.name }}</a></p>
