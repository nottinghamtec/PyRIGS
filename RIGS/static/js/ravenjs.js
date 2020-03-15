var querystring = require('querystring'),
	RavenClient = require('./lib/RavenClient'),
	HiLoIdGenerator = require('./lib/HiLoIdGenerator'),
	filter = require('./lib/filter')
	errorCodes = require('./lib/errorCodes'),
	_ = require('lodash'),
	inflect = require('i')();

var settings = {
	host: 'http://localhost:80',
	idFinder: defaultIdFinder,
	idGenerator: defaultIdGenerator,
	useOptimisticConcurrency: false
};

function defaultIdFinder(doc) {
	if (!doc) return undefined;
	if (doc['@metadata'] && doc['@metadata']['@id']) return doc['@metadata']['@id'];
	if (doc.hasOwnProperty('id')) return doc.id;
	if (doc.hasOwnProperty('Id')) return doc.Id;
}

function defaultIdGenerator(doc, settings, callback) {
	if (!doc) throw Error('Expected a valid doc object.');
	if (!settings) throw Error('Expected a valid setings object.');
	if (!settings.host) throw Error('Invalid settings. Expected host property.');
	if (!callback || !_(callback).isFunction) throw Error('Exepected a valid callback function.');

	var generator = new HiLoIdGenerator(settings);
	generator.nextId(function(error, id) {
		if (error) return callback(error);
		collectionName = '';
		if (!!doc && !!doc['@metadata'] && _.isString(doc['@metadata']['Raven-Entity-Name'])) collectionName = inflect.camelize(inflect.underscore(doc['@metadata']['Raven-Entity-Name']), false) + '/';
		id = collectionName + id;
		return callback(undefined, id.toString());
	});
}

exports.connectionString = function(connStr) {
	var self = this;
	if (!arguments.length) return settings.host;
	if (!_.isString(connStr)) throw new Error('Expected a valid raven connection string');

	var values = querystring.parse(connStr, ';', '=');
	if (!values.Url) throw new Error('Required connection string property "Url" was not specified!');

	self.host(values.Url);
	self.database(values.Database);
	self.username(values.UserName);
	self.password(values.Password);
	self.apiKey(values.ApiKey);
};
 
exports.host = function(host) {
	if (!arguments.length) return settings.host;
	if (!_.isString(host)) throw new Error('Expected a valid raven host name');
	if (!~host.indexOf('http://') && !~host.indexOf('https://')) throw new Error('Expected a host address with http:// or https://');
	settings.host = host;
};

exports.database = function(database) {
	if (!arguments.length) return settings.database;
	if (!database) {
		if (settings.database) delete settings.database;
		return;
	}

	if (!_.isString(database)) throw new Error('Expected a string for database name');
	settings.database = database;
};

exports.username = function(username) {
	if (!arguments.length) return settings.username;
	if (!username) {
		if (settings.username) delete settings.username;
		return;
	}

	if (!_.isString(username)) throw new Error('Expected a string for username');
	settings.username = username;
};

exports.password = function(password) {
	if (!arguments.length) return settings.password;
	if (!password) {
		if (settings.password) delete settings.password;
		return;
	}

	if (!_.isString(password)) throw new Error('Expected a string for password');
	settings.password = password;
};

exports.apiKey = function(apiKey) {
	if (!arguments.length) return settings.apiKey;
	if (!apiKey) {
		if(settings.apiKey) delete settings.apiKey;
		return;
	}

	if (!_.isString(apiKey)) throw new Error('Expected a string for apiKey');
	settings.apiKey = apiKey;
};

exports.idFinder = function(fn) {
	if (!fn) return settings.idFinder = defaultidFinder;
	if (!_(fn).isFunction()) throw new Error('Expected a valid function to use as the default key finder.');
	settings.idFinder = fn;
};

exports.idGenerator = function(fn) {
	if (!fn) return settings.idGenerator = defaultIdGenerator;
	if (!_(fn).isFunction()) throw new Error('Expected a valid function to use as the default key generator.');
	settings.idGenerator = fn;
};

exports.useOptimisticConcurrency= function(val) {
	if (!val) return settings.useOptimisticConcurrency;
	if (!_(val).isBoolean()) throw new Error('Expected a boolean value when setting useOptimisticConcurrency');
	settings.useOptimisticConcurrency = val;
};

exports.proxy = function(val) {
	if(!val) return settings.proxy;
	if (!_.isString(val)) throw new Error('Expected a valid proxy host address.');
	if (!~val.indexOf('http://') && !~val.indexOf('https://')) throw new Error("Invaid proxy address scheme. Expected http or https scheme.");
	settings.proxy = val;
};

exports.configure = function(env, fn) {
	if (_(env).isFunction()) {
		fn = env;
		env = 'all';
	}

	var currentEnv = process.env.NODE_ENV || 'development';
	if ('all' === env || ~env.indexOf(currentEnv)) fn.call(this);
};

//exposing default key finder and generator.
exports.defaultIdFinder = defaultIdFinder;

exports.defaultIdGenerator = defaultIdGenerator;

exports.connect = function(options) {
	var self = this;
	var clientSettings = _(settings).clone();
	if (_(options).isObject()) {
		clientSettings.host = options.host || clientSettings.host;
		clientSettings.database = options.database || clientSettings.database;
		clientSettings.username = options.username || clientSettings.username;
		clientSettings.password = options.password || clientSettings.password;
		clientSettings.apiKey = options.apiKey || clientSettings.apiKey;
		clientSettings.idFinder = options.idFinder || clientSettings.idFinder;
		clientSettings.idGenerator = options.idGenerator || clientSettings.idGenerator;
		clientSettings.proxy = options.proxy || clientSettings.proxy;
		clientSettings.useOptimisticConcurrency = options.useOptimisticConcurrency || clientSettings.useOptimisticConcurrency;
	}
	
	return new RavenClient(clientSettings);
};

exports.create = function(typeName, collectionName) {
	var doc = {},
		metadata = {},
		singular = false;
	if (!!typeName) {
		if (!_(typeName).isString()) throw new Error('Expected a valid string for typeName');
		metadata['Raven-Clr-Type'] = typeName;
	}
	if (_(collectionName).isBoolean()) {
		singular = collectionName === false;
		collectionName = undefined;
	}
	if (!!collectionName) {
		if (!_(collectionName).isString()) throw new Error('Expected a valid string or bool for collectionName');
		metadata['Raven-Entity-Name'] = collectionName;
	} else if (!!typeName) {
		if (!singular) {
			collectionName = inflect.pluralize(typeName);
		} else {
			collectionName = typeName;
		}
		metadata['Raven-Entity-Name'] = collectionName;
	}
	
	if (!_.isEmpty(metadata)) doc['@metadata'] = metadata;
	return doc;
};

exports.errorCodes = errorCodes;