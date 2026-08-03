<h3>Candidate Hired</h3>
<p>Dear {{ doc.owner }},</p>
<p><strong>{{ doc.candidate_name }}</strong> has been hired!</p>
<p><strong>Email:</strong> {{ doc.email }}</p>
<p><strong>Phone:</strong> {{ doc.phone }}</p>
<p><strong>Current Title:</strong> {{ doc.current_title }}</p>
<br>
<p>The candidate has been moved to <strong>Selected</strong> status and the recruitment process is complete.</p>
<p>View Candidate: <a href="/app/candidate/{{ doc.name }}">{{ doc.candidate_name }}</a></p>
