<h3>Offer Generated</h3>
<p>Dear {{ doc.owner }},</p>
<p>An offer has been generated for candidate <strong>{{ doc.candidate_name }}</strong>.</p>
<p><strong>Position:</strong> {{ doc.job_title }}</p>
<p><strong>Total CTC:</strong> {{ doc.total_ctc }}</p>
<p><strong>Status:</strong> {{ doc.status }}</p>
<p><strong>Approval Status:</strong> {{ doc.approval_status }}</p>
<br>
<p>View Offer: <a href="/app/offer-management/{{ doc.name }}">{{ doc.name }}</a></p>
