## :blue_book: Documentation

Export the following environment variables: 
* `POLARIS_SUBDOMAIN`
* `POLARIS_USERNAME`
* `POLARIS_PASSWORD`

The values of `POLARIS_SUBDOMAIN`, `USERNAME`, and `PASSWORD` can also be assigned in *polaris-ec2native-ondemand.py* if you are retrieving from a secret store programatically somehow.

Ensure you set `snapcount` equal to the number of snapshots you want to retain, and enable or disable logging by setting `logging` equal to True or False in *polaris-ec2native-ondemand.py*

Once configured, run this script using Python 3.6+ from an EC2 instance being protected by Polaris. Each time it is run, it will take an on demand snapshot of this instance and expire (starting with the oldest) any on demand snapshots this instance in excess of `snapcount`. 

For example, if `snapcount` was set to 5, and you had daily on demand snapshots from Monday Tuesday Wednesday Thursday and Friday. Running this script on Saturday would take a new on demand snapshot, as well as expire the on demand snapshot from Monday. In the same scenario if `snapcont` was set to 4, the snapshots from Monday and Tuesday would be expired.

## :muscle: How You Can Help

We glady welcome contributions from the community. From updating the documentation to adding more functions for Python, all ideas are welcome. Thank you in advance for all of your issues, pull requests, and comments! :star:

* [Contributing Guide](CONTRIBUTING.md)
* [Code of Conduct](CODE_OF_CONDUCT.md)

## :pushpin: License

* [MIT License](LICENSE)

## :point_right: About Rubrik Build

We encourage all contributors to become members. We aim to grow an active, healthy community of contributors, reviewers, and code owners. Learn more in our [Welcome to the Rubrik Build Community](https://github.com/rubrikinc/welcome-to-rubrik-build) page.

We'd  love to hear from you! Email us: build@rubrik.com :love_letter:
