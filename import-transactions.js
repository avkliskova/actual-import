let path = require('path');
let actual = require('@actual-app/api');

let dirname = '/root/actual-server/';

const args = process.argv.slice(2);
let data = require(args[0]);


async function main() {
	await actual.init({
		config: { dataDir: path.join(dirname, 'user-files') }
	});

	await actual.internal.send('load-budget', { id: '8c412ea0-7ee7-4bec-8ded-fbd09430326e' });
	const accounts = await actual.getAccounts();
	await actual.internal.send('api/accounts-get').then( accounts => {
		const acctId = accounts[0].id;
		actual.internal.send('transactions-import', {accountId: acctId, transactions: data} ).then( imported => {
			console.log(imported);
			// console.log(`Imported ${imported.length} transactions.`);
		}).then( nothing => actual.internal.send('close-budget') );
	});

}

main();
