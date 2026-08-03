<h3>Offer Accepted</h3>
<p>Dear {{ doc.owner }},</p>
<p>Candidate <strong>{{ doc.candidate_name }}</strong> has <strong>accepted</strong> the offer for <strong>{{ doc.job_title }}</strong>.</p>
<p><strong>Total CTC:</strong> {{ doc.total_ctc }}</p>
<p><strong>Expected Joining Date:</strong> {{ doc.expected_joining_date }}</p>
<p><strong>Response Date:</strong> {{ doc.candidate_response_date }}</p>
<br>
<p>Congratulations on the successful hire!</p>
<p>View Offer: <a href="/app/offer-management/{{ doc.name }}">{{ doc.name }}</a></p>
