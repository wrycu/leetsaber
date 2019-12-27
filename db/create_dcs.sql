CREATE TABLE `missions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `map` varchar(45) NOT NULL,
  `start_time` char(5) DEFAULT NULL,
  `playable_factions` tinyint(4) NOT NULL,
  `format` varchar(45) NOT NULL,
  `digest` char(32) NOT NULL,
  `path` varchar(400) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `digest_UNIQUE` (`digest`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE `modules` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL,
  `type` enum('fixed_wing','rotary_wing','ground','other') NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=latin1;

CREATE TABLE `dcs`.`mission_module_count` (
  `mission_id` INT NOT NULL,
  `module_id` INT NOT NULL,
  `module_count` INT NOT NULL,
  INDEX `fk_mission_id_idx` (`mission_id` ASC),
  INDEX `fk_module_id_idx` (`module_id` ASC),
  CONSTRAINT `fk_mission_id`
    FOREIGN KEY (`mission_id`)
    REFERENCES `dcs`.`missions` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_module_id`
    FOREIGN KEY (`module_id`)
    REFERENCES `dcs`.`modules` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION);

INSERT INTO dcs.modules (name, type) VALUES
('SRS', 'other'),
('CA', 'ground'),
('ATC', 'other'),
('F/A-18C', 'fixed_wing'),
('M-2000', 'fixed_wing'),
('AV-8B', 'fixed_wing'),
('A-10C', 'fixed_wing'),
('MiG-21', 'fixed_wing'),
('F-14', 'fixed_wing'),
('F-5', 'fixed_wing'),
('AJS37', 'fixed_wing'),
('MiG-19', 'fixed_wing'),
('F-16', 'fixed_wing'),
('FC-3 or 4', 'fixed_wing'),
('F-15C', 'fixed_wing'),
('Su-27', 'fixed_wing'),
('A-4E', 'fixed_wing'),
('Su-25T', 'fixed_wing'),
('Ka-50', 'rotary_wing'),
('Huey', 'rotary_wing'),
('Mi-8', 'rotary_wing'),
('Gazelle', 'fixed_wing'),
('F-86', 'fixed_wing'),
('MiG-15', 'fixed_wing'),
('Spitfire', 'fixed_wing'),
('Bf-109', 'fixed_wing'),
('P-51', 'fixed_wing'),
('FW-190', 'fixed_wing'),
('I-16', 'fixed_wing'),
('L-39', 'fixed_wing'),
('C-101', 'fixed_wing'),
('Yak-52', 'fixed_wing'),
('CE2', 'fixed_wing'),
('Hawk', 'fixed_wing'),
('JF-17', 'fixed_wing')
